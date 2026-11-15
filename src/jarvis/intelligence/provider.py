"""Optional bounded OpenAI-compatible structured intent provider."""

import json
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import OpenerDirector, Request

from jarvis.intelligence.intent import Intent


class ProviderError(Exception):
    pass


@dataclass(frozen=True)
class ProviderResult:
    intent: Intent
    total_tokens: int | None = None


class Provider(Protocol):
    def interpret(self, text: str) -> ProviderResult: ...


class MockProvider:
    def interpret(self, text: str) -> ProviderResult:
        return ProviderResult(Intent("assistant_status"), 0)


class OpenAIProvider:
    def __init__(self, url: str, model: str, api_key: str, timeout: float = 15.0) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Provider URL must use HTTPS without embedded credentials")
        if not model or not api_key or not 0 < timeout <= 120:
            raise ValueError("Provider requires model, credential, and bounded timeout")
        self.url, self.model, self.api_key, self.timeout = url, model, api_key, timeout

    def interpret(self, text: str) -> ProviderResult:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": 'Return JSON only: {"action": "assistant_status"} '
                    'or {"action":"open_website","target":"youtube"} or '
                    '{"action":"open_application","target":"notepad"}. No shell commands.',
                },
                {"role": "user", "content": text},
            ],
            "response_format": {"type": "json_object"},
        }
        # URL validated as HTTPS at construction.
        request = Request(  # noqa: S310
            self.url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        try:
            # Redirects are rejected to keep credentials on the configured destination.
            with _opener().open(request, timeout=self.timeout) as response:
                raw = response.read(65537)
            if len(raw) > 65536:
                raise ProviderError("Provider response too large")
            body = json.loads(raw)
            content = json.loads(body["choices"][0]["message"]["content"])
            if not isinstance(content, dict) or set(content) - {"action", "target"}:
                raise ValueError("Invalid intent fields")
            action, target = content["action"], content.get("target")
            if not isinstance(action, str) or (target is not None and not isinstance(target, str)):
                raise ValueError("Invalid intent types")
            usage_data = body.get("usage", {})
            if not isinstance(usage_data, dict):
                raise ValueError("Invalid usage metadata")
            usage = usage_data.get("total_tokens")
            if usage is not None and (type(usage) is not int or usage < 0):
                raise ValueError("Invalid token count")
            return ProviderResult(Intent(action, target), usage)
        except (
            HTTPError,
            URLError,
            TimeoutError,
            OSError,
            ValueError,
            KeyError,
            IndexError,
            TypeError,
        ) as exc:
            raise ProviderError("Provider request failed or returned invalid data") from exc


def _opener() -> OpenerDirector:
    from urllib.request import HTTPRedirectHandler, build_opener

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
            return None

    return build_opener(NoRedirect())
