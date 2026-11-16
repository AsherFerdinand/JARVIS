import multiprocessing

import pytest
from provider_harness import MockProviderServer

from jarvis.actions.windows import MockExecutor
from jarvis.config import Config
from jarvis.core.lifecycle import Assistant
from jarvis.intelligence.conversation import CloudConversation, Conversation
from jarvis.speech.session import State
from jarvis.speech.setup import endpoint_from_environment, make_voice


def controller(server, monkeypatch):
    for key, value in server.settings().items():
        monkeypatch.setenv(key, value)
    assistant = Assistant(
        Config(),
        MockExecutor(),
        conversation=Conversation(CloudConversation(endpoint_from_environment("JARVIS_AI"))),
    )
    return make_voice(assistant, mock_audio=True)


@pytest.mark.parametrize(
    "text,roles",
    [("Open YouTube.", ["STT", "TTS"]), ("Explain regenerative braking.", ["STT", "AI", "TTS"])],
)
def test_actual_http_voice_pipeline(monkeypatch, text, roles):
    with MockProviderServer(text) as server:
        voice = controller(server, monkeypatch)
        voice.start()
        result = voice.wait(10)
        assert result.state.current == State.COMPLETED
        assert server.calls == roles
        events = voice.assistant.events.snapshot()[1:]
        assert all(e.session_id == result.session_id for e in events)
        assert events[-2].event == "voice.session.completed"
        assert events[-1].event == "assistant.idle"
        assert all("audio" not in e.to_dict() for e in events)
        assert not any(p.name == "jarvis-provider" for p in multiprocessing.active_children())
        if "AI" in roles:
            assert result.response == "Synthetic explanation."
            assert len(voice.assistant.conversation.history) == 1
            assert not voice.assistant.executor.calls
        voice.close()


@pytest.mark.parametrize(
    "role,fault,code",
    [
        ("STT", "auth", "authentication_failed"),
        ("STT", "rate", "rate_limited"),
        ("AI", "server", "server_error"),
        ("STT", "malformed", "malformed_response"),
        ("TTS", "malformed", "invalid_audio_response"),
    ],
)
def test_real_http_errors_and_session_recovery(monkeypatch, role, fault, code):
    with MockProviderServer("Explain a concept.", (role, fault)) as server:
        voice = controller(server, monkeypatch)
        voice.start()
        result = voice.wait(10)
        assert result.state.current == State.FAILED
        assert result.error_code == code
        assert not voice.conversation.history
        assert server.calls.count(role) == 1  # POSTs cannot retry
        assert voice.assistant.events.snapshot()[-1].event == "assistant.idle"
        server.fault = None
        voice.start()
        assert voice.wait(10).state.current == State.COMPLETED
        voice.close()


def test_network_interruption_and_cancelled_slow_response(monkeypatch):
    with MockProviderServer(fault=("STT", "disconnect")) as server:
        voice = controller(server, monkeypatch)
        voice.start()
        assert voice.wait(10).state.current == State.FAILED
        server.fault = ("STT", "slow")
        server.entered.clear()
        voice.start()
        assert server.entered.wait(5)
        voice.cancel()
        assert voice.wait(3).state.current == State.CANCELLED
        assert not voice.assistant.executor.calls
        assert not any(p.name == "jarvis-provider" for p in multiprocessing.active_children())
        voice.close()


def test_minimal_profile_omits_optional_fields_and_accepts_text(monkeypatch):
    with MockProviderServer() as server:
        monkeypatch.setenv("JARVIS_STT_PROFILE", "compatible")
        monkeypatch.setenv("JARVIS_TTS_PROFILE", "compatible")
        monkeypatch.setenv("JARVIS_STT_RESPONSE_FORMAT", "text")
        voice = controller(server, monkeypatch)
        voice.start()
        assert voice.wait(10).state.current == State.COMPLETED
        assert server.fields == [
            {"role": "STT", "language_present": False, "format": "text"},
            {"role": "TTS", "speed_present": False},
        ]
        voice.close()


def test_real_http_cli_pipeline_without_devices(tmp_path):
    import os
    import sys
    from pathlib import Path

    from provider_harness import executable_pipeline

    executable = Path(sys.executable).parent / ("jarvis.exe" if os.name == "nt" else "jarvis")
    report = executable_pipeline(executable, tmp_path)
    assert report["paid_calls"] == 0
    assert all(case["state"] == "completed" for case in report["pipeline_cases"])
    assert report["audio_devices_opened"] == 0
