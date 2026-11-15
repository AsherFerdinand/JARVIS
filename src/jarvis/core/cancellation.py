"""Cooperative cancellation with an atomic side-effect commit boundary."""

from collections.abc import Callable
from threading import Event, RLock
from typing import TypeVar

T = TypeVar("T")


class Cancelled(Exception):
    pass


class Cancellation:
    def __init__(self) -> None:
        self.event = Event()
        self._lock = RLock()

    def cancel(self) -> None:
        # A successful check in commit is the side-effect linearization point.
        # Cancellation never waits for an already committed OS operation.
        self.event.set()

    def check(self) -> None:
        if self.event.is_set():
            raise Cancelled("Session cancelled")

    def commit(self, operation: Callable[[], T]) -> T:
        with self._lock:
            self.check()
            return operation()
