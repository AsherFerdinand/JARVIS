"""Replaceable speech boundaries only; no audio or models loaded."""

from typing import Protocol


class SpeechToText(Protocol):
    def transcribe(self, audio: bytes) -> str: ...


class TextToSpeech(Protocol):
    def synthesize(self, text: str) -> bytes: ...


class WakeWord(Protocol):
    def detect(self, audio: bytes) -> bool: ...


class Microphone(Protocol):
    def capture(self) -> bytes: ...
    def close(self) -> None: ...


class AudioOutput(Protocol):
    def play(self, audio: bytes) -> None: ...
    def close(self) -> None: ...
