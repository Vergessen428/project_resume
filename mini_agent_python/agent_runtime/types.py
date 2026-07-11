from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Message:
    role: str
    content: str
    name: Optional[str] = None


@dataclass
class ToolCall:
    name: str
    args: Dict[str, Any]


@dataclass
class ModelResponse:
    kind: str
    content: str = ""
    tool_call: Optional[ToolCall] = None

    @classmethod
    def final(cls, content: str) -> "ModelResponse":
        return cls(kind="final", content=content)

    @classmethod
    def call_tool(cls, name: str, args: Dict[str, Any]) -> "ModelResponse":
        return cls(kind="tool_call", tool_call=ToolCall(name=name, args=args))


@dataclass
class ToolResult:
    ok: bool
    content: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "content": self.content,
            "error": self.error,
        }


@dataclass
class ToolContext:
    workspace_root: str


ToolHandler = Callable[[Dict[str, Any], ToolContext], ToolResult]


@dataclass
class Tool:
    name: str
    description: str
    schema: Dict[str, Any]
    handler: ToolHandler


@dataclass
class ModelRequest:
    messages: List[Message]
    tools: List[Tool]
    original_goal: str
    skill_texts: List[str]
    tool_history: List[Dict[str, Any]]


@dataclass
class RunState:
    run_id: str
    session_id: str
    user_id: str
    original_goal: str
    messages: List[Message] = field(default_factory=list)
    tool_history: List[Dict[str, Any]] = field(default_factory=list)

