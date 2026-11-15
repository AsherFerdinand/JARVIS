"""Only these capabilities can cross the reasoning/execution boundary."""

from jarvis.config import Config
from jarvis.intelligence.intent import Intent

ACTIONS = frozenset(
    {
        "open_website",
        "open_application",
        "application_status",
        "system_info",
        "assistant_status",
        "exit",
    }
)


def validate(intent: Intent, config: Config) -> None:
    if intent.action not in ACTIONS:
        raise ValueError("Unapproved action")
    if intent.action == "open_website":
        if intent.target not in config.websites:
            raise ValueError("Unapproved website")
    elif intent.action in {"open_application", "application_status"}:
        if intent.target not in config.applications:
            raise ValueError("Unapproved application")
    elif intent.target is not None:
        raise ValueError("Unexpected target")
