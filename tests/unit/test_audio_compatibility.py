import struct
from threading import Event
from types import SimpleNamespace

import pytest

from jarvis.actions.windows import MockExecutor
from jarvis.config import Config
from jarvis.core.cancellation import Cancellation, Cancelled
from jarvis.core.lifecycle import Assistant
from jarvis.core.voice_controller import VoiceController
from jarvis.speech.audio import PCM, AudioError, convert_pcm, decode_wav
from jarvis.speech.audio_capture import DevicePlayback, MicrophoneCapture
from jarvis.speech.audio_devices import choose_format, inventory
from jarvis.speech.mocks import MockSTT, MockTTS
from jarvis.speech.session import State


class Devices:
    def __init__(self):
        self.default = SimpleNamespace(device=[0, 1])
        self.rows = [
            {
                "name": "USB microphone",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 48000,
            },
            {
                "name": "Speakers",
                "max_input_channels": 0,
                "max_output_channels": 2,
                "default_samplerate": 48000,
            },
            {
                "name": "Bluetooth headset",
                "max_input_channels": 1,
                "max_output_channels": 2,
                "default_samplerate": 16000,
            },
        ]
        self.queries = 0
        self.closed = []
        self.writes = []
        self.on_capture = lambda: None
        self.on_write = lambda: None

    def query_devices(self):
        self.queries += 1
        return self.rows

    def check_input_settings(self, **options):
        if options["samplerate"] != 48000 or options["channels"] != 1:
            raise ValueError("unsupported")

    def check_output_settings(self, **options):
        if options["samplerate"] != 48000 or options["channels"] != 2:
            raise ValueError("unsupported")

    def RawInputStream(self, **options):
        owner = self

        class Input:
            active = True

            def __enter__(self):
                options["callback"](memoryview(b"\x10\x00" * 128), 128, None, False)
                owner.on_capture()
                return self

            def __exit__(self, *args):
                owner.closed.append(("input", options["device"]))

        return Input()

    def RawOutputStream(self, **options):
        owner = self

        class Output:
            def __enter__(self):
                return self

            def write(self, data):
                owner.writes.append((options["device"], options["samplerate"], options["channels"]))
                owner.on_write()
                return False

            def abort(self):
                owner.closed.append(("abort", options["device"]))

            def __exit__(self, *args):
                owner.closed.append(("output", options["device"]))

        return Output()


def test_realistic_device_sequence_and_lazy_activation(monkeypatch):
    devices = Devices()
    monkeypatch.setattr("jarvis.speech.audio_capture.audio_backend", lambda: devices)
    voice = VoiceController(
        Assistant(Config(), MockExecutor()),
        MicrophoneCapture(),
        MockSTT("status"),
        MockTTS(),
        DevicePlayback(),
    )
    devices.on_capture = voice.release
    assert devices.queries == 0
    voice.start()
    assert voice.wait(3).state.current == State.COMPLETED
    devices.rows[0]["max_input_channels"] = 0
    voice.start()
    assert voice.wait(3).state.current == State.FAILED
    devices.rows[0]["max_input_channels"] = 1
    voice.start()
    assert voice.wait(3).state.current == State.COMPLETED
    devices.default.device[1] = 2  # Bluetooth-like output switch, fresh selection next session
    voice.start()
    assert voice.wait(3).state.current == State.COMPLETED
    assert devices.writes[-1][0] == 2
    devices.on_write = voice.cancel
    voice.start()
    assert voice.wait(3).state.current == State.CANCELLED
    assert ("abort", 2) in devices.closed
    voice.close()
    assert sum(kind == "input" for kind, _ in devices.closed) == 4
    assert sum(kind == "output" for kind, _ in devices.closed) == 4


def test_explicit_selection_never_falls_back(monkeypatch):
    devices = Devices()
    devices.rows[0]["max_input_channels"] = 0
    devices.default.device[0] = 2
    with pytest.raises(AudioError) as error:
        choose_format(devices, "USB microphone", "input", 16000, 1)
    assert error.value.code == "audio_input_unavailable"
    assert choose_format(devices, "index:2", "input", 16000, 1).device == 2


@pytest.mark.parametrize("broken", ["channels", "rate", "name", "list"])
def test_corrupted_enumeration_is_sanitized(broken):
    devices = Devices()
    if broken == "channels":
        devices.rows[0]["max_input_channels"] = "secret"
    if broken == "rate":
        devices.rows[0]["default_samplerate"] = float("nan")
    if broken == "name":
        devices.rows[0]["name"] = None
    if broken == "list":
        devices.rows = {"secret": "bad"}
    with pytest.raises(AudioError) as error:
        inventory(devices)
    assert error.value.code == "audio_enumeration_failed"
    assert "secret" not in str(error.value)


def test_wrong_channels_unsupported_rates_and_ambiguous_names():
    devices = Devices()

    def unsupported(**options):
        raise ValueError("unsupported")

    devices.check_input_settings = unsupported
    with pytest.raises(AudioError) as error:
        choose_format(devices, None, "input", 16000, 1)
    assert error.value.code == "audio_input_format_unsupported"
    devices.rows[2]["name"] = "USB microphone"
    with pytest.raises(AudioError) as error:
        choose_format(devices, "USB microphone", "input", 16000, 1)
    assert error.value.code == "audio_device_ambiguous"


def test_stereo_capture_when_mono_is_not_supported(monkeypatch):
    devices = Devices()
    devices.rows[0]["max_input_channels"] = 2

    def stereo(**options):
        if options["channels"] != 2:
            raise ValueError("stereo only")

    devices.check_input_settings = stereo
    release = Event()
    devices.on_capture = release.set
    monkeypatch.setattr("jarvis.speech.audio_capture.audio_backend", lambda: devices)
    pcm = decode_wav(MicrophoneCapture().record(release, Cancellation(), 1))
    assert pcm.channels == 2


def test_pcm_conversion_values_bounds_and_cancel():
    pcm = PCM(struct.pack("<hh", 0, 1000), 8000, 1)
    converted = convert_pcm(pcm, 16000, 2, Cancellation())
    assert struct.unpack("<hhhhhhhh", converted.data) == (0, 0, 500, 500, 1000, 1000, 1000, 1000)
    stereo = PCM(struct.pack("<hhhh", 1000, -1000, 2000, 4000), 16000, 2)
    assert struct.unpack("<hh", convert_pcm(stereo, 16000, 1, Cancellation()).data) == (0, 3000)
    cancel = Cancellation()
    cancel.cancel()
    with pytest.raises(Cancelled):
        convert_pcm(pcm, 16000, 1, cancel)
    with pytest.raises(AudioError):
        convert_pcm(PCM(b"\x00\x00" * 1000000, 8000, 1), 48000, 2, Cancellation())


def test_explicit_index_cannot_silently_rebind_to_different_microphone(monkeypatch):
    devices = Devices()
    release = Event()
    devices.on_capture = release.set
    monkeypatch.setattr("jarvis.speech.audio_capture.audio_backend", lambda: devices)
    capture = MicrophoneCapture("index:0")
    assert capture.record(release, Cancellation(), 1)
    devices.rows[0]["name"] = "Different microphone after hotplug"
    release.clear()
    with pytest.raises(AudioError) as error:
        capture.record(release, Cancellation(), 1)
    assert error.value.code == "audio_device_changed"
    assert len(devices.closed) == 1
