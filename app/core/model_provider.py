"""Build the active model client from environment variables.

Reads GEMINI/OPENAI/DEEPSEEK/OPENROUTER/CUSTOM keys and MODEL_FALLBACK_ORDER,
then returns a single client or a FailoverModelClient across the configured
providers. This is the only place provider wiring lives.
"""

import os

from .models import FailoverModelClient, GeminiModelClient, OpenAICompatibleModelClient


def load_dotenv(path: str) -> None:
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def build_model():
    providers = {}
    if os.environ.get("GEMINI_API_KEY"):
        providers["gemini"] = GeminiModelClient()
    if os.environ.get("OPENAI_API_KEY"):
        providers["openai"] = OpenAICompatibleModelClient(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
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

    for provider_name, client in providers.items():
        # Single-provider clients do not have FailoverModelClient.active_provider.
        # Keep the same factual metadata contract for both paths.
        client.provider_name = provider_name

    default_order = "gemini,openai,deepseek,openrouter,custom"
    order = [item.strip().lower() for item in os.environ.get("MODEL_FALLBACK_ORDER", default_order).split(",") if item.strip()]
    selected = [(name, providers[name]) for name in order if name in providers]
    if not selected:
        raise RuntimeError("未找到可用模型。请至少配置 GEMINI_API_KEY 或一个备用模型 API Key。")
    return selected[0][1] if len(selected) == 1 else FailoverModelClient(selected)
