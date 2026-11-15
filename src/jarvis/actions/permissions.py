"""Sensitive capabilities remain denied even if a caller claims confirmation."""

from jarvis.actions.registry import validate
from jarvis.config import Config
from jarvis.intelligence.intent import Intent


def authorize(intent: Intent, config: Config) -> None:
    # v0.1 registers only low-risk actions. Future sensitive actions must use a
    # separate, user-bound confirmation mechanism before joining this boundary.
    validate(intent, config)
