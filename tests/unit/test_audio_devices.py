from threading import Event
from types import SimpleNamespace

import pytest

from jarvis.core.cancellation import Cancellation, Cancelled
from jarvis.speech.audio import AudioError, decode_wav, synthetic_wav
from jarvis.speech.audio_capture import DevicePlayback, MicrophoneCapture
from jarvis.speech.audio_devices import audio_backend


def test_missing_optional_audio_dependency(monkeypatch):
    def missing(name):
        raise ImportError("missing")

    monkeypatch.setattr("jarvis.speech.audio_devices.import_module", missing)
    with pytest.raises(AudioError):
        audio_backend()


def test_microphone_records_only_until_release_and_closes(monkeypatch):
    release, cancel = Event(), Cancellation()
    calls = []

    class Stream:
        def __init__(self, **options):
            calls.append(options)
            self.callback = options["callback"]

        def __enter__(self):
            self.callback(memoryview(decode_wav(synthetic_wav()).data), 1600, None, False)
            release.set()
            return self

        def __exit__(self, *args):
            calls.append("closed")

    monkeypatch.setattr(
        "jarvis.speech.audio_capture.audio_backend", lambda: SimpleNamespace(RawInputStream=Stream)
    )
    audio = MicrophoneCapture("input").record(release, cancel, 1)
    assert decode_wav(audio).data
    assert calls[0]["device"] == "input"
    assert calls[-1] == "closed"


def test_microphone_limit_bounds_callback_buffer(monkeypatch):
    release = Event()

    class Stream:
        def __init__(self, **kwargs):
            self.callback = kwargs["callback"]

        def __enter__(self):
            self.callback(memoryview(b"\x10\x00" * 40000), 40000, None, False)
            release.set()

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(
        "jarvis.speech.audio_capture.audio_backend", lambda: SimpleNamespace(RawInputStream=Stream)
    )
    assert len(decode_wav(MicrophoneCapture().record(release, Cancellation(), 1)).data) == 32000


def test_device_failure_is_safe(monkeypatch):
    def broken(**kwargs):
        raise RuntimeError("private-device-detail")

    monkeypatch.setattr(
        "jarvis.speech.audio_capture.audio_backend", lambda: SimpleNamespace(RawInputStream=broken)
    )
    with pytest.raises(AudioError, match="Microphone unavailable"):
        MicrophoneCapture().record(Event(), Cancellation(), 1)


def test_cancelled_playback_aborts_and_closes(monkeypatch):
    cancel = Cancellation()
    calls = []

    class Output:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def write(self, data):
            cancel.cancel()
            return False

        def abort(self):
            calls.append("abort")

        def __exit__(self, *args):
            calls.append("closed")

    monkeypatch.setattr(
        "jarvis.speech.audio_capture.audio_backend", lambda: SimpleNamespace(RawOutputStream=Output)
    )
    with pytest.raises(Cancelled):
        DevicePlayback().play(synthetic_wav(), cancel)
    assert calls == ["abort", "closed"]
