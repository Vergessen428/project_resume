"""Text-completion model clients for the interview assistant.

Only what the assistant needs: a single-prompt `complete()` call, provider
failover, and enough attributes (api_key / base_url / model / get_provider) for
the modules that talk to Gemini's native Files and Search APIs directly.
"""

import json
import os
import time
import urllib.request
from typing import Dict, List, Optional, Sequence, Tuple


class ModelClient:
    def complete(self, prompt: str) -> str:
        raise NotImplementedError


class OpenAICompatibleModelClient(ModelClient):
    """Minimal OpenAI-compatible chat client using only the standard library."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        required_key_name: str = "OPENAI_API_KEY",
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.required_key_name = required_key_name
        if not self.api_key:
            raise RuntimeError("%s is required for this model client." % self.required_key_name)

    def complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        }
        body = json.dumps(payload).encode("utf-8")
        url = self.base_url.rstrip("/") + "/chat/completions"
        http_request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": "Bearer %s" % self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(http_request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
        message = data["choices"][0]["message"]
        content = message.get("content") or ""
        if isinstance(content, list):
            content = "\n".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
        return str(content).strip()


class GeminiModelClient(OpenAICompatibleModelClient):
    """Gemini through Google's OpenAI-compatible endpoint."""

    def __init__(self) -> None:
        super().__init__(
            api_key=os.environ.get("GEMINI_API_KEY", ""),
            base_url=os.environ.get(
                "GEMINI_OPENAI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta/openai",
            ),
            model=os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite"),
            required_key_name="GEMINI_API_KEY",
        )


class FailoverModelClient(ModelClient):
    """Tries configured providers in order, switching only on a transport/API failure.

    A normal model answer is returned as-is and never silently overwritten.
    """

    def __init__(self, providers: Sequence[Tuple[str, ModelClient]]) -> None:
        if not providers:
            raise RuntimeError("至少需要配置一个模型 API。")
        self.providers = list(providers)
        self.provider_names = [name for name, _ in self.providers]
        self.active_provider = self.providers[0][0]
        self.model = getattr(self.providers[0][1], "model", self.active_provider)
        self._cooldown_until: Dict[str, float] = {}

    def get_provider(self, name: str) -> Optional[ModelClient]:
        for provider_name, client in self.providers:
            if provider_name == name:
                return client
        return None

    def complete(self, prompt: str) -> str:
        errors: List[str] = []
        now = time.monotonic()
        candidates = [item for item in self.providers if self._cooldown_until.get(item[0], 0) <= now]
        if not candidates:
            candidates = self.providers
        for name, client in candidates:
            try:
                content = client.complete(prompt)
                self.active_provider = name
                self.model = getattr(client, "model", name)
                return content
            except Exception as exc:
                # A short circuit breaker avoids repeatedly spending time on an API
                # that is currently rate-limited or unavailable.
                self._cooldown_until[name] = time.monotonic() + 60
                errors.append("%s: %s" % (name, type(exc).__name__))
        raise RuntimeError("所有已配置模型暂时不可用（%s）。" % ", ".join(errors))
