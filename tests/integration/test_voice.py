import json
import subprocess
import sys
from threading import Barrier, Event, Thread
from urllib.request import Request, urlopen

import pytest

from jarvis.actions.windows import MockExecutor
from jarvis.config import Config
from jarvis.core.lifecycle import Assistant
from jarvis.core.voice_controller import PushToTalkAdapter, VoiceController
from jarvis.integration.protocol import LEGACY_EVENT_TYPES
from jarvis.integration.server import EventServer
from jarvis.intelligence.conversation import Conversation, Reply
from jarvis.speech.audio import AudioError, synthetic_wav
from jarvis.speech.audio_capture import FileCapture, MockCapture, MockPlayback
from jarvis.speech.mocks import MockSTT, MockTTS
from jarvis.speech.session import SessionState, State


def make_controller(text="Open YouTube.", **kwargs):
    assistant = Assistant(Config(), MockExecutor())
    return VoiceController(
        assistant,
        kwargs.pop("capture", MockCapture()),
        kwargs.pop("stt", MockSTT(text)),
        kwargs.pop("tts", MockTTS()),
        kwargs.pop("playback", MockPlayback()),
        **kwargs,
    )


def test_voice_approved_pipeline_and_events():
    controller = make_controller(share_transcript=True)
    session = controller.start()
    result = controller.wait(3)
    assert result.state.history == [
        State.IDLE,
        State.LISTENING,
        State.TRANSCRIBING,
        State.PROCESSING,
        State.EXECUTING,
        State.SPEAKING,
        State.COMPLETED,
    ]
    assert result.recognized_text == "Open YouTube."
    assert controller.assistant.executor.calls == [("website", "https://www.youtube.com")]
    events = controller.assistant.events.snapshot()[1:]
    assert {e.session_id for e in events} == {session}
    assert {e.correlation_id for e in events} == {session}
    assert events[-2].event == "voice.session.completed"
    assert events[-1].event == "assistant.idle"
    assert any(e.recognized_text == "Open YouTube." for e in events)
    assert "speech" in result.timings_ms
    assert not controller.busy


@pytest.mark.parametrize(
    "text",
    [
        "Open YouTube?",
        "open youtube or notepad",
        "don't open youtube",
        "open powershell",
        "delete all files",
        "open youtube; rm -rf /",
    ],
)
def test_ambiguity_and_unsafe_commands_never_execute(text):
    controller = make_controller(text)
    controller.start()
    result = controller.wait(3)
    assert result.state.current == State.FAILED
    assert not controller.assistant.executor.calls


@pytest.mark.parametrize("text", ["Open Notepad.", "Öffne Notepad.", "Show system information."])
def test_voice_deterministic_commands_bypass_paid_ai(text):
    class NoCalls:
        def respond(self, messages, cancel):
            raise AssertionError("Deterministic command was sent to provider")

    controller = make_controller(text, conversation=Conversation(NoCalls()))
    controller.start()
    assert controller.wait(3).state.current == State.COMPLETED


def test_ai_text_cannot_become_an_action():
    class Malicious:
        def respond(self, messages, cancel):
            return Reply("powershell Remove-Item C:\\important; open youtube", 20)

    controller = make_controller("explain a concept", conversation=Conversation(Malicious()))
    controller.start()
    result = controller.wait(3)
    assert result.state.current == State.COMPLETED
    assert result.total_tokens == 20
    assert not controller.assistant.executor.calls
    assert not any(e.recognized_text for e in controller.assistant.events.snapshot())


def test_capture_release_cancel_and_recovery():
    entered, closed = Event(), Event()

    class HeldCapture:
        def record(self, release, cancel, seconds):
            entered.set()
            try:
                assert release.wait(3)
                cancel.check()
                return synthetic_wav()
            finally:
                closed.set()

    controller = make_controller(capture=HeldCapture())
    adapter = PushToTalkAdapter(controller)
    adapter.press()
    assert entered.wait(3)
    with pytest.raises(RuntimeError):
        adapter.press()
    adapter.cancel()
    assert controller.wait(3).state.current == State.CANCELLED
    assert closed.is_set()
    assert not controller.assistant.executor.calls
    controller.capture = MockCapture()
    adapter.press()
    adapter.release()
    assert controller.wait(3).state.current == State.COMPLETED


def test_late_transcription_discarded_and_worker_bound():
    entered, answer = Event(), Event()

    class LateSTT:
        def transcribe(self, audio, cancel):
            entered.set()
            assert answer.wait(3)
            return "open youtube"

    controller = make_controller(stt=LateSTT())
    controller.start()
    assert entered.wait(3)
    controller.cancel()
    with pytest.raises(RuntimeError):
        controller.start()
    with pytest.raises(TimeoutError):
        controller.wait(0)
    answer.set()
    assert controller.wait(3).state.current == State.CANCELLED
    assert not controller.assistant.executor.calls
    assert not any(
        e.event == "voice.transcription.completed" for e in controller.assistant.events.snapshot()
    )


def test_playback_cancellation_events():
    entered = Event()

    class HeldPlayback:
        def play(self, audio, cancel):
            entered.set()
            assert cancel.event.wait(3)
            cancel.check()

    controller = make_controller(playback=HeldPlayback())
    controller.start()
    assert entered.wait(3)
    controller.cancel()
    assert controller.wait(3).state.current == State.CANCELLED
    events = [e.event for e in controller.assistant.events.snapshot()]
    assert "voice.playback.cancelled" in events
    assert "voice.playback.completed" not in events
    assert events[-2:] == ["voice.session.cancelled", "assistant.idle"]


@pytest.mark.parametrize("phase", ["capture", "stt", "tts", "playback"])
def test_failure_cleanup_and_terminal_state(phase):
    class Broken:
        def record(self, *args):
            raise AudioError("unavailable")

        def transcribe(self, *args):
            raise TimeoutError("timeout")

        def synthesize(self, *args):
            raise TimeoutError("timeout")

        def play(self, *args):
            raise AudioError("unavailable")

    controller = make_controller(**{phase: Broken()})
    controller.start()
    result = controller.wait(3)
    assert result.state.current == State.FAILED
    assert controller.assistant.events.snapshot()[-1].event == "assistant.idle"
    assert result.error_code in {"voice_failure", "audio_failure"}
    controller.close()
    assert not controller.busy


def test_prerecorded_synthetic_wav(tmp_path):
    path = tmp_path / "synthetic.wav"
    path.write_bytes(synthetic_wav())
    controller = make_controller(capture=FileCapture(path))
    controller.start()
    assert controller.wait(3).state.current == State.COMPLETED


def test_state_machine_rejects_invalid_and_terminal_transitions():
    state = SessionState()
    with pytest.raises(ValueError):
        state.move(State.SPEAKING)
    state.move(State.LISTENING)
    state.move(State.CANCELLED)
    with pytest.raises(ValueError):
        state.move(State.IDLE)


def test_simultaneous_activation_single_worker():
    barrier, entered, release = Barrier(3), Event(), Event()

    class HeldSTT:
        def transcribe(self, audio, cancel):
            entered.set()
            assert release.wait(3)
            return "status"

    controller = make_controller(stt=HeldSTT())
    outcomes = []

    def activate():
        barrier.wait()
        try:
            controller.start()
            outcomes.append("started")
        except RuntimeError:
            outcomes.append("rejected")

    threads = [Thread(target=activate), Thread(target=activate)]
    for thread in threads:
        thread.start()
    barrier.wait()
    assert entered.wait(3)
    for thread in threads:
        thread.join(3)
    release.set()
    assert controller.wait(3).state.current == State.COMPLETED
    assert sorted(outcomes) == ["rejected", "started"]


def test_event_channel_preserves_legacy_shape():
    controller = make_controller(share_transcript=True)
    controller.start()
    controller.wait(3)
    token = "a" * 48
    server = EventServer(controller.assistant.events, token)
    server.start()
    try:

        def get(path):
            request = Request(
                f"http://127.0.0.1:{server.port}{path}",
                headers={"Authorization": f"Bearer {token}"},
            )
            with urlopen(request, timeout=3) as response:
                return json.load(response)["events"]

        legacy = get("/v1/events")
        assert all(e["event"] in LEGACY_EVENT_TYPES for e in legacy)
        assert all("session_id" not in e and "recognized_text" not in e for e in legacy)
        extended = get("/v1/voice-events")
        assert any(e.get("recognized_text") == "Open YouTube." for e in extended)
        assert all("audio" not in e for e in extended)
    finally:
        server.close()


def test_mock_voice_cli_no_credentials_no_device():
    result = subprocess.run(
        [sys.executable, "-m", "jarvis.main", "--mock-voice", "Open YouTube.", "--diagnostics"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout.splitlines()[0] == "Website opened (mock)"
    assert json.loads(result.stdout.splitlines()[1])["state"] == "completed"


def test_voice_requires_explicit_configuration(monkeypatch):
    from jarvis.speech.setup import make_voice

    for field in ("URL", "MODEL", "KEY"):
        monkeypatch.delenv(f"JARVIS_STT_{field}", raising=False)
    with pytest.raises(ValueError):
        make_voice(Assistant(Config(), MockExecutor()))


def test_cancelled_conversation_discards_late_response():
    entered, release = Event(), Event()

    class LateChat:
        def respond(self, messages, cancel):
            entered.set()
            assert release.wait(3)
            return Reply("late answer", 100)

    conversation = Conversation(LateChat())
    playback = MockPlayback()
    controller = make_controller("explain a concept", conversation=conversation, playback=playback)
    controller.start()
    assert entered.wait(3)
    controller.cancel()
    release.set()
    assert controller.wait(3).state.current == State.CANCELLED
    assert not conversation.history
    assert not playback.completed


def test_cancelled_synthesis_never_reaches_playback():
    entered, release = Event(), Event()

    class LateTTS:
        def synthesize(self, text, cancel):
            entered.set()
            assert release.wait(3)
            return synthetic_wav()

    playback = MockPlayback()
    controller = make_controller(tts=LateTTS(), playback=playback)
    controller.start()
    assert entered.wait(3)
    controller.cancel()
    release.set()
    assert controller.wait(3).state.current == State.CANCELLED
    assert not playback.completed


def test_disabled_speech_does_not_import_or_open_devices():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, threading; import jarvis.main; "
            'assert "sounddevice" not in sys.modules; '
            'assert not any(t.name == "jarvis-voice" for t in threading.enumerate())',
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_german_action_confirmation_is_spoken_in_german():
    spoken = []

    class RecordingTTS(MockTTS):
        def synthesize(self, text, cancel):
            spoken.append(text)
            return super().synthesize(text, cancel)

    controller = make_controller("Öffne YouTube.", language="de", tts=RecordingTTS())
    controller.start()
    assert controller.wait(3).state.current == State.COMPLETED
    assert spoken == ["Webseite geöffnet."]
