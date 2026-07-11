import os
import time
import uuid
from typing import Dict, Optional

from .context import build_context
from .logs import JsonlLogger
from .models import ModelClient
from .policy import PolicyEngine, PolicyError
from .skills import SkillLoader
from .tools import ToolRegistry
from .types import Message, RunState, ToolContext, ToolResult


class AgentRuntime:
    def __init__(
        self,
        model: ModelClient,
        tools: ToolRegistry,
        policy: PolicyEngine,
        logger: JsonlLogger,
        skill_loader: SkillLoader,
        workspace_root: str,
        max_steps: int = 8,
    ) -> None:
        self.model = model
        self.tools = tools
        self.policy = policy
        self.logger = logger
        self.skill_loader = skill_loader
        self.workspace_root = os.path.realpath(workspace_root)
        self.max_steps = max_steps
        self.last_run_id: Optional[str] = None

    def run(
        self,
        user_input: str,
        session_id: str = "default",
        user_id: str = "local-user",
    ) -> str:
        run = RunState(
            run_id=self._new_run_id(),
            session_id=session_id,
            user_id=user_id,
            original_goal=user_input,
            messages=[Message(role="user", content=user_input)],
        )
        self.last_run_id = run.run_id
        skill_texts = self.skill_loader.load_for_goal(user_input)

        self.logger.write(
            run.run_id,
            "user_message",
            {"session_id": session_id, "user_id": user_id, "content": user_input},
        )
        self.logger.write(
            run.run_id,
            "skills_loaded",
            {"count": len(skill_texts)},
        )

        for step in range(self.max_steps):
            request = build_context(run, self.tools.list(), skill_texts)
            response = self.model.generate(request)

            self.logger.write(
                run.run_id,
                "model_response",
                self._response_to_log(step, response.kind, response.content, response.tool_call),
            )

            if response.kind == "final":
                run.messages.append(Message(role="assistant", content=response.content))
                self.logger.write(run.run_id, "final_answer", {"content": response.content})
                return response.content

            if response.kind == "tool_call" and response.tool_call is not None:
                tool_call = response.tool_call

                result = self._execute_tool(run, tool_call.name, tool_call.args)
                run.tool_history.append(
                    {
                        "name": tool_call.name,
                        "args": tool_call.args,
                        "result": result.to_dict(),
                    }
                )
                continue

            fallback = "模型返回了 runtime 无法识别的结果，任务停止。"
            self.logger.write(run.run_id, "runtime_error", {"error": fallback})
            return fallback

        final = "任务停止：已达到最大执行步数 %s。请缩小任务范围或提高 max steps。" % self.max_steps
        self.logger.write(run.run_id, "max_steps_reached", {"content": final})
        return final

    def _execute_tool(self, run: RunState, name: str, args: Dict[str, object]) -> ToolResult:
        try:
            self.policy.check(name, args, current_tool_calls=len(run.tool_history))
        except PolicyError as exc:
            result = ToolResult(ok=False, content="", error=str(exc))
            self.logger.write(
                run.run_id,
                "policy_denied",
                {"tool": name, "args": args, "error": str(exc)},
            )
            return result

        self.logger.write(run.run_id, "tool_call", {"tool": name, "args": args})
        result = self.tools.execute(
            name,
            args,
            ToolContext(workspace_root=self.workspace_root),
        )
        self.logger.write(
            run.run_id,
            "tool_result",
            {"tool": name, "args": args, "result": result.to_dict()},
        )
        return result

    def _response_to_log(
        self,
        step: int,
        kind: str,
        content: str,
        tool_call: Optional[object],
    ) -> Dict[str, object]:
        data: Dict[str, object] = {"step": step, "kind": kind, "content": content}
        if tool_call is not None:
            data["tool_call"] = {
                "name": getattr(tool_call, "name", ""),
                "args": getattr(tool_call, "args", {}),
            }
        return data

    def _new_run_id(self) -> str:
        return "%s-%s" % (int(time.time()), uuid.uuid4().hex[:8])
