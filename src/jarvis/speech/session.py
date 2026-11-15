"""Explicit single-session state machine; instances are never reused."""

from dataclasses import dataclass, field
from enum import StrEnum


class State(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    PROCESSING = "processing"
    EXECUTING = "executing"
    SPEAKING = "speaking"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL = frozenset({State.COMPLETED, State.FAILED, State.CANCELLED})
TRANSITIONS = {
    State.IDLE: {State.LISTENING},
    State.LISTENING: {State.TRANSCRIBING},
    State.TRANSCRIBING: {State.PROCESSING},
    State.PROCESSING: {State.EXECUTING, State.SPEAKING, State.COMPLETED},
    State.EXECUTING: {State.SPEAKING, State.COMPLETED},
    State.SPEAKING: {State.COMPLETED},
}


@dataclass
class SessionState:
    current: State = State.IDLE
    history: list[State] = field(default_factory=lambda: [State.IDLE])

    def move(self, target: State) -> None:
        if self.current in TERMINAL:
            raise ValueError("Session already terminal")
        if target not in TRANSITIONS.get(self.current, set()) | {State.FAILED, State.CANCELLED}:
            raise ValueError("Invalid voice transition")
        self.current = target
        self.history.append(target)
