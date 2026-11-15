from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    action: str
    target: str | None = None
