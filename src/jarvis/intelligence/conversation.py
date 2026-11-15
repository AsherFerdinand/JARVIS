"""Text-only conversation output never reaches the action executor."""

import json
from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from jarvis.core.cancellation import Cancellation
from jarvis.intelligence.provider import ProviderError
from jarvis.speech.cloud import Endpoint


@dataclass(frozen=True)
class Reply:
    text: str
    total_tokens: int | None = None


@dataclass(frozen=True)
class PendingTurn:
    question: str
    reply: Reply
    generation: int


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
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError) as exc:
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
        self._lock = Lock()
        self._generation = 0
        self._turns: list[tuple[str, str]] = []
        self.total_tokens = 0

    @property
    def history(self) -> tuple[tuple[str, str], ...]:
        with self._lock:
            return tuple(self._turns)

    def clear(self) -> None:
        with self._lock:
            self._turns.clear()
            self._generation += 1

    def respond(self, text: str, cancel: Cancellation) -> Reply:
        pending = self.prepare(text, cancel)
        self.commit_turn(pending, cancel)
        return pending.reply

    def prepare(self, text: str, cancel: Cancellation) -> PendingTurn:
        if not text.strip() or len(text) > 4096:
            raise ValueError("Conversation input must contain 1–4096 characters")
        cancel.check()
        with self._lock:
            context, generation = list(self._turns), self._generation
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

        cancel.check()
        return PendingTurn(text, reply, generation)

    def commit_turn(self, pending: PendingTurn, cancel: Cancellation) -> None:
        def save() -> None:
            with self._lock:
                if pending.generation != self._generation:
                    return
                self._turns.append((pending.question, pending.reply.text))
                while (
                    len(self._turns) > self.max_turns
                    or sum(len(a) + len(b) for a, b in self._turns) > self.max_characters
                ):
                    self._turns.pop(0)
                self.total_tokens += pending.reply.total_tokens or 0

        cancel.commit(save)
