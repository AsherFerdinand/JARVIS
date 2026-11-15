"""Optional bounded OpenAI-compatible structured intent provider."""

import json
from dataclasses import dataclass
from typing import Protocol

from jarvis.core.cancellation import Cancellation
from jarvis.intelligence.errors import ProviderError as ProviderError
from jarvis.intelligence.intent import Intent
from jarvis.intelligence.transport import Endpoint, Transport


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
    def __init__(
        self,
        url: str,
        model: str,
        api_key: str,
        timeout: float = 15.0,
        transport: Transport | None = None,
    ) -> None:
        self.endpoint = Endpoint(url, api_key, model, timeout, transport=transport)
        self.model = model

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
        raw = self.endpoint.post(json.dumps(payload).encode(), "application/json", Cancellation())
        try:
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
        except (ValueError, KeyError, IndexError, TypeError, AttributeError, RecursionError) as exc:
            raise ProviderError("Provider returned invalid data") from exc
