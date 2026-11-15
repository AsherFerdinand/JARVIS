"""Text-only conversation output never reaches the action executor."""

import json
from dataclasses import dataclass
from typing import Protocol

from jarvis.core.cancellation import Cancellation
from jarvis.intelligence.provider import ProviderError
from jarvis.speech.cloud import Endpoint


@dataclass(frozen=True)
class Reply:
    text: str
    total_tokens: int | None = None


class ChatProvider(Protocol):
    def respond(self, messages: list[dict[str, str]], cancel: Cancellation) -> Reply: ...


class CloudConversation:
    def __init__(self, endpoint: Endpoint) -> None:
        self.endpoint = endpoint

    def respond(self, messages: list[dict[str, str]], cancel: Cancellation) -> Reply:
        payload = json.dumps({"model": self.endpoint.model, "messages": messages}).encode()
        raw = self.endpoint.post(payload, "application/json", cancel)
        try:
            body = json.loads(raw)
            text = body["choices"][0]["message"]["content"]
            usage = body.get("usage", {})
            if not isinstance(usage, dict):
                raise ValueError("Invalid usage metadata")
            tokens = usage.get("total_tokens")
            if not isinstance(text, str) or not text.strip() or len(text) > 4096:
                raise ValueError("Invalid conversation response")
            if tokens is not None and (type(tokens) is not int or tokens < 0):
                raise ValueError("Invalid token count")
            return Reply(text, tokens)
        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
            raise ProviderError("Invalid conversation response") from exc


class MockConversation:
    def respond(self, messages: list[dict[str, str]], cancel: Cancellation) -> Reply:
        cancel.check()
        return Reply("This is a mock conversational response.", 0)


class Conversation:
    def __init__(
        self,
        provider: ChatProvider,
        max_turns: int = 6,
        max_characters: int = 16000,
        language: str = "en",
    ) -> None:
        if not 1 <= max_turns <= 32 or not 8192 <= max_characters <= 65536:
            raise ValueError("Invalid history bounds")
        if language not in {"en", "de"}:
            raise ValueError("Supported languages are en and de")
        self.provider, self.max_turns, self.max_characters = provider, max_turns, max_characters
        self.language = language
        self._turns: list[tuple[str, str]] = []
        self.total_tokens = 0

    @property
    def history(self) -> tuple[tuple[str, str], ...]:
        return tuple(self._turns)

    def clear(self) -> None:
        self._turns.clear()

    def respond(self, text: str, cancel: Cancellation) -> Reply:
        if not text.strip() or len(text) > 4096:
            raise ValueError("Conversation input must contain 1–4096 characters")
        cancel.check()
        context = list(self._turns)
        while (
            context and sum(len(a) + len(b) for a, b in context) + len(text) > self.max_characters
        ):
            context.pop(0)
        messages = [
            {
                "role": "system",
                "content": f"Reply in {self.language}. "
                "Provide concise plain text. You cannot execute tools or operating-system actions.",
            }
        ]
        for question, answer in context:
            messages.extend(
                [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
            )
        messages.append({"role": "user", "content": text})
        reply = self.provider.respond(messages, cancel)
        if not reply.text.strip() or len(reply.text) > 4096:
            raise ProviderError("Invalid conversation response")

        def save() -> None:
            self._turns.append((text, reply.text))
            while (
                len(self._turns) > self.max_turns
                or sum(len(a) + len(b) for a, b in self._turns) > self.max_characters
            ):
                self._turns.pop(0)
            self.total_tokens += reply.total_tokens or 0

        cancel.commit(save)
        return reply
