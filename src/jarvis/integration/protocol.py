import time
import uuid
from dataclasses import asdict, dataclass

LEGACY_EVENT_TYPES = frozenset(
    {
        "assistant.idle",
        "assistant.listening",
        "assistant.processing",
        "assistant.speaking",
        "command.executing",
        "command.completed",
        "command.failed",
    }
)

EVENT_TYPES = LEGACY_EVENT_TYPES | frozenset(
    {
        "assistant.transcribing",
        "voice.transcription.completed",
        "voice.session.completed",
        "voice.session.failed",
        "voice.session.cancelled",
        "voice.playback.completed",
        "voice.playback.cancelled",
    }
)


@dataclass(frozen=True)
class Event:
    version: int
    id: str
    timestamp: float
    correlation_id: str
    event: str
    application: str | None = None
    display_text: str | None = None
    icon: str | None = None
    progress: float | None = None

    session_id: str | None = None
    recognized_text: str | None = None
    error_info: str | None = None

    def __post_init__(self) -> None:
        if self.version != 1 or self.event not in EVENT_TYPES:
            raise ValueError("Unsupported event protocol")
        if not self.correlation_id or not self.id or self.timestamp < 0:
            raise ValueError("Invalid event metadata")
        if self.progress is not None and not 0 <= self.progress <= 1:
            raise ValueError("Invalid progress")

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in ("session_id", "recognized_text", "error_info"):
            if result[key] is None:
                del result[key]
        return result


def event(
    kind: str,
    correlation_id: str,
    application: str | None = None,
    *,
    session_id: str | None = None,
    recognized_text: str | None = None,
    error_info: str | None = None,
) -> Event:
    return Event(
        1,
        str(uuid.uuid4()),
        time.time(),
        correlation_id,
        kind,
        application,
        session_id=session_id,
        recognized_text=recognized_text,
        error_info=error_info,
    )
