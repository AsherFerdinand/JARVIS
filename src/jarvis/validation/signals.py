"""Bounded local test signal and content-free PCM levels."""

import math
import sys
from array import array
from threading import Event

from jarvis.core.cancellation import Cancellation
from jarvis.speech.audio import AudioError, decode_wav, encode_wav


def tone(seconds: float = 0.5, volume: float = 0.03) -> bytes:
    if not math.isfinite(seconds) or not 0 < seconds <= 2:
        raise ValueError("Tone duration must be >0 and <=2 seconds")
    if not math.isfinite(volume) or not 0.005 <= volume <= 0.1:
        raise ValueError("Tone amplitude must be 0.005–0.1 full scale")
    rate = 16000
    frames = max(1, int(rate * seconds))
    samples = array("h")
    for index in range(frames):
        fade = min(1.0, index / 160, (frames - 1 - index) / 160)
        samples.append(round(32767 * volume * fade * math.sin(2 * math.pi * 440 * index / rate)))
    if sys.byteorder != "little":
        samples.byteswap()
    return encode_wav(samples.tobytes(), rate)


def inspect_signal(audio: bytes) -> dict[str, int | float | bool | None]:
    pcm = decode_wav(audio)
    values = array("h")
    values.frombytes(pcm.data)
    if sys.byteorder != "little":
        values.byteswap()
    if not values:
        raise AudioError("Empty sample")
    rms = math.sqrt(sum(value * value for value in values) / len(values)) / 32768
    peak = max(abs(value) for value in values) / 32768
    return {
        "sample_rate": pcm.rate,
        "channels": pcm.channels,
        "wav_bytes": len(audio),
        "duration_seconds": len(values) / (pcm.rate * pcm.channels),
        "peak_full_scale": peak,
        "rms_dbfs": 20 * math.log10(rms) if rms else None,
        "clipped_fraction": sum(abs(value) >= 32760 for value in values) / len(values),
        "signal_detected": rms >= 10 ** (-55 / 20),
        "speech_quality_verified": False,
    }


class SyntheticCapture:
    """Explicit simulation with measurable signal; never accesses a device."""

    def record(self, release: Event, cancel: Cancellation, seconds: float) -> bytes:
        cancel.check()
        return tone(min(seconds, 0.5))
