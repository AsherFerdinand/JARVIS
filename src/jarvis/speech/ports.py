"""Cancellable speech adapters. v0.1 byte-only interfaces remain available."""

from threading import Event
from typing import Protocol

from jarvis.core.cancellation import Cancellation


class Capture(Protocol):
    def record(self, release: Event, cancel: Cancellation, seconds: float) -> bytes: ...


class Transcriber(Protocol):
    def transcribe(self, audio: bytes, cancel: Cancellation) -> str: ...


class Synthesizer(Protocol):
    def synthesize(self, text: str, cancel: Cancellation) -> bytes: ...


class Playback(Protocol):
    def play(self, audio: bytes, cancel: Cancellation) -> None: ...
