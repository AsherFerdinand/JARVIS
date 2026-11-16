"""Explicit activation only. Bounded capture and no disk recordings."""

import time
from pathlib import Path
from threading import Event

from jarvis.core.cancellation import Cancellation, Cancelled
from jarvis.speech.audio import (
    MAX_AUDIO_BYTES,
    AudioError,
    convert_pcm,
    decode_wav,
    encode_wav,
    synthetic_wav,
)
from jarvis.speech.audio_devices import audio_backend, bind_identity, choose_format, managed_stream


class FileCapture:
    def __init__(self, path: Path) -> None:
        self.path = path

    def record(self, release: Event, cancel: Cancellation, seconds: float) -> bytes:
        cancel.check()
        with self.path.open("rb") as source:
            audio = source.read(MAX_AUDIO_BYTES + 1)
        pcm = decode_wav(audio, require_sound=True)
        if len(pcm.data) / (pcm.rate * pcm.channels * 2) > seconds:
            raise AudioError("Audio exceeds recording limit")
        cancel.check()
        return audio


class MockCapture:
    def record(self, release: Event, cancel: Cancellation, seconds: float) -> bytes:
        cancel.check()
        return synthetic_wav()


class MicrophoneCapture:
    def __init__(self, device: str | None = None) -> None:
        self.device = device
        self._identity: tuple[str, int] | None = None

    def record(self, release: Event, cancel: Cancellation, seconds: float) -> bytes:
        if not 0 < seconds <= 60:
            raise AudioError("Recording duration must be 0–60 seconds")
        cancel.check()
        backend = audio_backend()
        selected = choose_format(backend, self.device, "input", 16000, 1)
        self._identity = bind_identity(self.device, self._identity, selected)
        frame_bytes = selected.channels * 2
        limit = (
            min(int(seconds * selected.rate), (MAX_AUDIO_BYTES - 128) // frame_bytes) * frame_bytes
        )
        duration = min(seconds, limit / (selected.rate * frame_bytes))
        buffer = bytearray()
        failure = Event()
        expected_stop = Event()
        started = False

        def callback(data: object, frames: int, timing: object, status: object) -> None:
            if status:
                failure.set()
                release.set()
                raise backend.CallbackStop
            if release.is_set() or cancel.event.is_set() or len(buffer) >= limit:
                expected_stop.set()
                release.set()
                raise backend.CallbackStop
            # Copy only the accepted slice, not an entire oversized input chunk.
            buffer.extend(memoryview(data).cast("B")[: limit - len(buffer)])  # type: ignore[arg-type]

        def finished() -> None:
            if not expected_stop.is_set() and not release.is_set() and not cancel.event.is_set():
                failure.set()
            release.set()

        try:
            with managed_stream(
                backend.RawInputStream(
                    samplerate=selected.rate,
                    channels=selected.channels,
                    dtype="int16",
                    blocksize=1024,
                    device=selected.device,
                    callback=callback,
                    finished_callback=finished,
                )
            ) as stream:
                started = True
                deadline = time.monotonic() + duration
                while not release.wait(min(0.05, max(0, deadline - time.monotonic()))):
                    cancel.check()
                    if time.monotonic() >= deadline:
                        break
                    if not getattr(stream, "active", True):
                        raise AudioError("Microphone disconnected", "audio_input_disconnected")
        except Cancelled:
            raise
        except AudioError:
            raise
        except Exception:
            cancel.check()
            code = "audio_input_interrupted" if started else "audio_input_unavailable"
            raise AudioError("Microphone unavailable or capture failed", code) from None
        cancel.check()
        if failure.is_set():
            raise AudioError("Microphone overflow or device failure", "audio_input_interrupted")
        audio = encode_wav(bytes(buffer), selected.rate, selected.channels)
        decode_wav(audio, require_sound=True)
        return audio


class DevicePlayback:
    def __init__(self, device: str | None = None) -> None:
        self.device = device
        self._identity: tuple[str, int] | None = None

    def play(self, audio: bytes, cancel: Cancellation) -> None:
        pcm = decode_wav(audio)
        cancel.check()
        backend = audio_backend()
        selected = choose_format(backend, self.device, "output", pcm.rate, pcm.channels)
        self._identity = bind_identity(self.device, self._identity, selected)
        pcm = convert_pcm(pcm, selected.rate, selected.channels, cancel)
        started = False
        try:
            with managed_stream(
                backend.RawOutputStream(
                    samplerate=pcm.rate,
                    channels=pcm.channels,
                    dtype="int16",
                    blocksize=1024,
                    device=selected.device,
                )
            ) as stream:
                started = True
                data = memoryview(pcm.data)
                step = 1024 * pcm.channels * 2
                try:
                    for offset in range(0, len(pcm.data), step):
                        cancel.check()
                        if stream.write(data[offset : offset + step]):
                            raise AudioError("Playback underflow")
                    cancel.check()
                except BaseException:
                    try:
                        stream.abort()
                    except Exception:  # noqa: S110 -- primary exception preserved, close still runs
                        pass  # Preserve the primary error; context exit still attempts close.
                    raise
        except Cancelled:
            raise
        except Exception:
            cancel.check()
            code = "audio_output_interrupted" if started else "audio_output_unavailable"
            raise AudioError("Speaker unavailable or playback failed", code) from None


class MockPlayback:
    def __init__(self) -> None:
        self.completed = False

    def play(self, audio: bytes, cancel: Cancellation) -> None:
        decode_wav(audio)
        cancel.check()
        self.completed = True
