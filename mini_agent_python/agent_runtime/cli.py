import argparse
import os
import sys

from .logs import JsonlLogger
from .loop import AgentRuntime
from .models import FailoverModelClient, GeminiModelClient, MockModelClient, OpenAICompatibleModelClient
from .policy import PolicyEngine
from .skills import SkillLoader
from .tools import build_default_tools


def load_dotenv(path: str) -> None:
    if not os.path.isfile(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def build_runtime(args: argparse.Namespace) -> AgentRuntime:
    project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
    load_dotenv(os.path.join(project_root, ".env"))

    workspace_root = os.path.realpath(args.workspace or os.path.join(project_root, "workspace"))
    logs_root = os.path.realpath(args.logs or os.path.join(project_root, "logs"))
    skills_root = os.path.realpath(args.skills or os.path.join(project_root, "skills"))

    model = _build_model_client(args.model)

    return AgentRuntime(
        model=model,
        tools=build_default_tools(),
        policy=PolicyEngine(workspace_root=workspace_root, max_tool_calls=args.max_tool_calls),
        logger=JsonlLogger(logs_root),
        skill_loader=SkillLoader(skills_root),
        workspace_root=workspace_root,
        max_steps=args.max_steps,
    )


def _build_model_client(requested_model: str):
    if requested_model == "mock":
        return MockModelClient()

    providers = {}
    if os.environ.get("GEMINI_API_KEY"):
        providers["gemini"] = GeminiModelClient()
    if os.environ.get("OPENAI_API_KEY"):
        providers["openai"] = OpenAICompatibleModelClient(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
            required_key_name="OPENAI_API_KEY",
        )
    if os.environ.get("DEEPSEEK_API_KEY"):
        providers["deepseek"] = OpenAICompatibleModelClient(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            required_key_name="DEEPSEEK_API_KEY",
        )
    if os.environ.get("OPENROUTER_API_KEY"):
        providers["openrouter"] = OpenAICompatibleModelClient(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            model=os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash"),
            required_key_name="OPENROUTER_API_KEY",
        )
    if os.environ.get("CUSTOM_MODEL_API_KEY") and os.environ.get("CUSTOM_MODEL_BASE_URL"):
        providers["custom"] = OpenAICompatibleModelClient(
            api_key=os.environ["CUSTOM_MODEL_API_KEY"],
            base_url=os.environ["CUSTOM_MODEL_BASE_URL"],
            model=os.environ.get("CUSTOM_MODEL_NAME", "custom-model"),
            required_key_name="CUSTOM_MODEL_API_KEY",
        )

    if requested_model == "openai" and "openai" not in providers:
        raise RuntimeError("OPENAI_API_KEY is required for --model openai.")

    default_order = "openai,gemini,deepseek,openrouter,custom" if requested_model == "openai" else "gemini,openai,deepseek,openrouter,custom"
    order = [item.strip().lower() for item in os.environ.get("MODEL_FALLBACK_ORDER", default_order).split(",") if item.strip()]
    selected = [(name, providers[name]) for name in order if name in providers]
    if not selected:
        raise RuntimeError("未找到可用模型。请至少配置 GEMINI_API_KEY 或一个备用模型 API Key。")
    return selected[0][1] if len(selected) == 1 else FailoverModelClient(selected)


def main(argv: object = None) -> int:
    parser = argparse.ArgumentParser(description="Mini Agent Runtime")
    parser.add_argument(
        "--model",
        choices=["mock", "openai", "gemini"],
        default="gemini",
        help="Model provider to use. Default: gemini.",
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--logs", default="")
    parser.add_argument("--skills", default="")
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-tool-calls", type=int, default=10)
    parser.add_argument("--once", default="", help="Run one task and exit.")
    args = parser.parse_args(argv)

    runtime = build_runtime(args)

    if args.once:
        answer = runtime.run(args.once)
        print(answer)
        return 0

    model_label = args.model
    if args.model == "gemini":
        model_label = "gemini (%s)" % getattr(runtime.model, "model", "configured model")
    print("Mini Agent Runtime. Model: %s. Type 'exit' to quit." % model_label)
    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if user_input.lower() in ("exit", "quit"):
            return 0

        if not user_input:
            continue

        answer = runtime.run(user_input)
        print(answer)


if __name__ == "__main__":
    sys.exit(main())
