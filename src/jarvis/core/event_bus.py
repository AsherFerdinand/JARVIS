"""Bounded in-memory history; no background worker or disk recording."""

from collections import deque
from threading import Lock

from jarvis.integration.protocol import Event


class EventBus:
    def __init__(self, capacity: int = 128) -> None:
        if not 1 <= capacity <= 4096:
            raise ValueError("Invalid history capacity")
        self._events: deque[Event] = deque(maxlen=capacity)
        self._lock = Lock()

    def publish(self, value: Event) -> None:
        with self._lock:
            self._events.append(value)

    def snapshot(self) -> list[Event]:
        with self._lock:
            return list(self._events)
