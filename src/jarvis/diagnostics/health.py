"""Sanitized optional health snapshots. Never emits config values or user content."""

import importlib.util
import os
from collections.abc import Mapping

from jarvis import __version__
from jarvis.core.event_bus import EventBus
from jarvis.diagnostics.resources import process_resources
from jarvis.speech.audio import AudioError
from jarvis.speech.audio_devices import audio_backend


def health(
    *,
    environment: Mapping[str, str] | None = None,
    events: EventBus | None = None,
    event_port: int | None = None,
    probe_audio: bool = False,
) -> dict[str, object]:
    settings = os.environ if environment is None else environment
    providers = {}
    for prefix in ("JARVIS_AI", "JARVIS_STT", "JARVIS_TTS"):
        presence = {
            field.lower(): bool(settings.get(f"{prefix}_{field}"))
            for field in ("URL", "MODEL", "KEY")
        }
        providers[prefix] = {
            "complete": all(presence.values()),
            "partial": any(presence.values()) and not all(presence.values()),
            "credential_present": presence["key"],
        }
    installed = importlib.util.find_spec("sounddevice") is not None
    backend = "not_probed" if installed else "not_installed"
    if probe_audio:
        try:
            audio_backend()
            backend = "available"
        except AudioError:
            backend = "unavailable"
    recent = [e.error_info for e in events.snapshot() if e.error_info] if events else []
    try:
        resources = process_resources()
    except OSError:
        resources = {"working_set_bytes": None, "private_bytes": None, "cpu_seconds": None}
    return {
        "version": __version__,
        "providers": providers,
        "audio_backend": backend,
        "selected_devices": {
            direction: "explicit" if settings.get(f"JARVIS_{direction}_DEVICE") else "default"
            for direction in ("INPUT", "OUTPUT")
        },
        "event_server": {"running": event_port is not None, "port": event_port},
        "recent_error_codes": recent[-8:],
        "process": resources,
    }
