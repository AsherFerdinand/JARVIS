"""Bounded PCM WAV validation shared by capture, cloud transport and playback."""

import io
import wave
from dataclasses import dataclass

from jarvis.core.cancellation import Cancellation

MAX_AUDIO_BYTES = 4_000_000
MAX_RECORD_SECONDS = 60


class AudioError(Exception):
    """Safe user-facing code; no provider payload or device identifiers."""

    def __init__(self, message: str, code: str = "audio_failure") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PCM:
    data: bytes
    rate: int
    channels: int


def encode_wav(data: bytes, rate: int = 16000, channels: int = 1) -> bytes:
    if channels not in (1, 2) or not 8000 <= rate <= 48000:
        raise AudioError("Unsupported PCM format")
    if len(data) > MAX_AUDIO_BYTES - 128 or len(data) % (channels * 2):
        raise AudioError("Invalid audio size")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(data)
    return buffer.getvalue()


def decode_wav(audio: bytes, *, require_sound: bool = False) -> PCM:
    if not 44 <= len(audio) <= MAX_AUDIO_BYTES:
        raise AudioError("Invalid audio size")
    try:
        with wave.open(io.BytesIO(audio), "rb") as source:
            channels, rate = source.getnchannels(), source.getframerate()
            if source.getsampwidth() != 2 or channels not in (1, 2) or not 8000 <= rate <= 48000:
                raise AudioError("Expected PCM16 mono/stereo WAV at 8–48 kHz")
            frames = source.getnframes()
            streaming = frames in {0x7FFFFFFF // (channels * 2), 0xFFFFFFFF // (channels * 2)}
            size = frames * channels * 2
            if not streaming and not 0 < size <= MAX_AUDIO_BYTES:
                raise AudioError("Invalid audio duration")
            data = source.readframes(min(frames, MAX_AUDIO_BYTES // (channels * 2)))
            if not streaming and len(data) != size:
                raise AudioError("Truncated WAV")
            if not data or len(data) % (channels * 2) or len(data) / (rate * channels * 2) > 120:
                raise AudioError("Invalid audio duration")
    except (wave.Error, EOFError, OSError) as exc:
        raise AudioError("Malformed WAV") from exc
    if require_sound and not any(data):
        raise AudioError("No speech detected")
    return PCM(data, rate, channels)


def synthetic_wav() -> bytes:
    # Small deterministic non-silent PCM fixture; contains no real voice.
    return encode_wav(b"\x10\x00\xf0\xff" * 800)


def convert_pcm(pcm: PCM, rate: int, channels: int, cancel: Cancellation) -> PCM:
    """Bounded linear PCM16 conversion for speech; not a studio anti-aliasing resampler."""
    import sys
    from array import array

    cancel.check()
    if (
        pcm.channels not in (1, 2)
        or not 8000 <= pcm.rate <= 48000
        or not pcm.data
        or len(pcm.data) % (pcm.channels * 2)
        or len(pcm.data) > MAX_AUDIO_BYTES
    ):
        raise AudioError("Invalid source PCM")
    if rate == pcm.rate and channels == pcm.channels:
        return pcm
    if not 8000 <= rate <= 48000 or channels not in (1, 2):
        raise AudioError("Unsupported conversion format", "audio_conversion_unsupported")
    source_frames = len(pcm.data) // (pcm.channels * 2)
    frames = max(1, source_frames * rate // pcm.rate)
    if frames * channels * 2 > MAX_AUDIO_BYTES:
        raise AudioError("Converted audio exceeds size bound", "audio_conversion_too_large")
    source = array("h")
    source.frombytes(pcm.data)
    if sys.byteorder != "little":
        source.byteswap()
    output = array("h")

    def value(frame: int, channel: int) -> int:
        if pcm.channels == 2 and channels == 1:
            return (source[frame * 2] + source[frame * 2 + 1]) // 2
        return source[frame * pcm.channels + min(channel, pcm.channels - 1)]

    for index in range(frames):
        if index % 1024 == 0:
            cancel.check()
        position, fraction = divmod(index * pcm.rate, rate)
        left = min(position, source_frames - 1)
        right = min(left + 1, source_frames - 1)
        for channel in range(channels):
            sample = (
                value(left, channel) * (rate - fraction) + value(right, channel) * fraction
            ) // rate
            output.append(sample)
    if sys.byteorder != "little":
        output.byteswap()
    cancel.check()
    return PCM(output.tobytes(), rate, channels)
