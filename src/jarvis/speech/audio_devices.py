"""PortAudio is imported only after explicit device use, never at core startup."""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib import import_module
from types import ModuleType

from jarvis.speech.audio import AudioError


def audio_backend() -> ModuleType:
    try:
        return import_module("sounddevice")
    except (ImportError, OSError) as exc:
        raise AudioError(
            "Audio backend unavailable; install audio extra and native PortAudio",
            "audio_backend_unavailable",
        ) from exc


def list_devices() -> str:
    try:
        return str(audio_backend().query_devices())
    except AudioError:
        raise
    except Exception as exc:
        raise AudioError("Audio devices unavailable") from exc


@dataclass(frozen=True)
class DeviceFormat:
    device: int | str | None
    rate: int
    channels: int
    identity: tuple[str, int] | None = field(default=None, repr=False)


@dataclass(frozen=True)
class Device:
    index: int
    name: str
    inputs: int
    outputs: int
    rate: float
    host_api: int = 0

    def channels(self, direction: str) -> int:
        return self.inputs if direction == "input" else self.outputs


def inventory(backend: ModuleType) -> list[Device]:
    try:
        rows = backend.query_devices()
        if not isinstance(rows, list | tuple):
            raise ValueError("Invalid device inventory")
        result = []
        for index, row in enumerate(rows):
            if (
                not isinstance(row, Mapping)
                or not isinstance(row.get("name"), str)
                or not row.get("name")
            ):
                raise ValueError("Invalid device record")
            item = dict(row)
            if type(item.get("hostapi", 0)) is not int or item.get("hostapi", 0) < 0:
                raise ValueError("Invalid host API")
            for key in ("max_input_channels", "max_output_channels"):
                if type(item.get(key)) is not int or not 0 <= item[key] <= 64:
                    raise ValueError("Invalid channel count")
            rate = item.get("default_samplerate")
            if (
                not isinstance(rate, int | float)
                or not math.isfinite(rate)
                or not 8000 <= rate <= 384000
            ):
                raise ValueError("Invalid device rate")
            result.append(
                Device(
                    index,
                    item["name"],
                    item["max_input_channels"],
                    item["max_output_channels"],
                    float(rate),
                    item.get("hostapi", 0),
                )
            )
        return result
    except Exception:
        raise AudioError(
            "Device enumeration unavailable or malformed", "audio_enumeration_failed"
        ) from None


def choose_format(
    backend: ModuleType, selection: str | None, direction: str, rate: int, channels: int
) -> DeviceFormat:
    # Older injected minimal adapters remain compatible. Real sounddevice always has these APIs.
    if not hasattr(backend, "query_devices"):
        return DeviceFormat(selection, rate, channels)
    rows = inventory(backend)
    try:
        if selection is None:
            index = int(backend.default.device[0 if direction == "input" else 1])
        elif selection.startswith("index:"):
            index = int(selection[6:])
        else:
            exact = [
                i
                for i, row in enumerate(rows)
                if row.name.casefold() == selection.casefold() and row.channels(direction) > 0
            ]
            matches = exact or [
                i
                for i, row in enumerate(rows)
                if selection.casefold() in row.name.casefold() and row.channels(direction) > 0
            ]
            if len(matches) > 1:
                raise AudioError("Selected device is ambiguous", "audio_device_ambiguous")
            if not matches:
                raise ValueError("Selected device missing")
            index = matches[0]
        if not 0 <= index < len(rows) or rows[index].channels(direction) < 1:
            raise ValueError("Device missing or wrong direction")
    except AudioError:
        raise
    except (ValueError, TypeError, AttributeError, IndexError):
        raise AudioError(
            "Selected/default device unavailable", f"audio_{direction}_unavailable"
        ) from None
    native = int(rows[index].rate)
    rates = list(dict.fromkeys([rate, native, 48000, 44100, 24000, 16000, 8000]))
    counts = list(dict.fromkeys([channels, 1, 2]))
    check = getattr(backend, f"check_{direction}_settings", None)
    if not callable(check):
        raise AudioError("Backend format checks unavailable", "audio_enumeration_failed")
    for candidate_rate in rates:
        if not 8000 <= candidate_rate <= 48000:
            continue
        for count in counts:
            if count > rows[index].channels(direction):
                continue
            try:
                check(device=index, channels=count, samplerate=candidate_rate, dtype="int16")
                return DeviceFormat(
                    index, candidate_rate, count, (rows[index].name, rows[index].host_api)
                )
            except Exception:  # noqa: S112 -- unsupported format; no sensitive driver messages
                continue
    raise AudioError(
        "No supported bounded PCM16 device format", f"audio_{direction}_format_unsupported"
    )


def audio_preflight(
    input_device: str | None = None, output_device: str | None = None
) -> dict[str, object]:
    report: dict[str, object] = {"streams_opened": 0, "hardware_verified": False}
    try:
        backend = audio_backend()
        rows = inventory(backend)
        report["device_count"] = len(rows)
        for direction, selection in (("input", input_device), ("output", output_device)):
            try:
                chosen = choose_format(backend, selection, direction, 16000, 1)
                report[direction] = {
                    "valid": True,
                    "index": chosen.device,
                    "rate": chosen.rate,
                    "channels": chosen.channels,
                }
            except AudioError as exc:
                report[direction] = {"valid": False, "error_code": exc.code}
    except AudioError as exc:
        report["error_code"] = exc.code
    return report


def bind_identity(
    selection: str | None, previous: tuple[str, int] | None, chosen: DeviceFormat
) -> tuple[str, int] | None:
    if selection is not None and chosen.identity is not None:
        if previous is not None and previous != chosen.identity:
            raise AudioError(
                "Explicit device identity changed; reselect device", "audio_device_changed"
            )
        return chosen.identity
    return previous
