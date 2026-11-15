"""PortAudio is imported only after explicit device use, never at core startup."""

from importlib import import_module
from types import ModuleType

from jarvis.speech.audio import AudioError


def audio_backend() -> ModuleType:
    try:
        return import_module("sounddevice")
    except (ImportError, OSError) as exc:
        raise AudioError("Audio backend unavailable; install the audio extra") from exc


def list_devices() -> str:
    try:
        return str(audio_backend().query_devices())
    except AudioError:
        raise
    except Exception as exc:
        raise AudioError("Audio devices unavailable") from exc
