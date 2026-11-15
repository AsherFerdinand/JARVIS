"""Explicit activation only. Bounded capture and no disk recordings."""

from pathlib import Path
from threading import Event

from jarvis.core.cancellation import Cancellation, Cancelled
from jarvis.speech.audio import MAX_AUDIO_BYTES, AudioError, decode_wav, encode_wav, synthetic_wav
from jarvis.speech.audio_devices import audio_backend


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

    def record(self, release: Event, cancel: Cancellation, seconds: float) -> bytes:
        if not 0 < seconds <= 60:
            raise AudioError("Recording duration must be 0–60 seconds")
        cancel.check()
        backend = audio_backend()
        limit = int(seconds * 16000) * 2
        buffer = bytearray()
        failure = Event()

        def callback(data: object, frames: int, timing: object, status: object) -> None:
            if status:
                failure.set()
                release.set()
                raise backend.CallbackStop
            if release.is_set() or cancel.event.is_set() or len(buffer) >= limit:
                raise backend.CallbackStop
            buffer.extend(bytes(data)[: limit - len(buffer)])  # type: ignore[call-overload]

        try:
            with backend.RawInputStream(
                samplerate=16000,
                channels=1,
                dtype="int16",
                blocksize=1024,
                device=self.device,
                callback=callback,
            ):
                # Controller cancellation also signals release. No busy polling.
                release.wait(seconds)
        except Exception as exc:
            raise AudioError("Microphone unavailable or capture failed") from exc
        cancel.check()
        if failure.is_set():
            raise AudioError("Microphone overflow or device failure")
        audio = encode_wav(bytes(buffer))
        decode_wav(audio, require_sound=True)
        return audio


class DevicePlayback:
    def __init__(self, device: str | None = None) -> None:
        self.device = device

    def play(self, audio: bytes, cancel: Cancellation) -> None:
        pcm = decode_wav(audio)
        cancel.check()
        backend = audio_backend()
        try:
            with backend.RawOutputStream(
                samplerate=pcm.rate,
                channels=pcm.channels,
                dtype="int16",
                blocksize=1024,
                device=self.device,
            ) as stream:
                step = 1024 * pcm.channels * 2
                try:
                    for offset in range(0, len(pcm.data), step):
                        cancel.check()
                        if stream.write(pcm.data[offset : offset + step]):
                            raise AudioError("Playback underflow")
                    cancel.check()
                except BaseException:
                    stream.abort()
                    raise
        except Cancelled:
            raise
        except Exception as exc:
            raise AudioError("Speaker unavailable or playback failed") from exc


class MockPlayback:
    def __init__(self) -> None:
        self.completed = False

    def play(self, audio: bytes, cancel: Cancellation) -> None:
        decode_wav(audio)
        cancel.check()
        self.completed = True
