import json
import sys

import pytest
from provider_harness import MockProviderServer

from jarvis.core.cancellation import Cancellation
from jarvis.main import main
from jarvis.speech.audio import encode_wav
from jarvis.speech.audio_capture import MockCapture, MockPlayback
from jarvis.validation.benchmark import benchmark
from jarvis.validation.runner import Consent, Validator
from jarvis.validation.signals import inspect_signal, tone


@pytest.mark.parametrize("stage", ["microphone", "speaker", "stt", "chat", "tts", "interaction"])
def test_consent_blocks_all_effects(stage):
    report = Validator({}).run(stage)
    assert report["outcome"] == "blocked"
    assert set(report["effects"].values()) == {"not_requested"}


@pytest.mark.parametrize(
    "seconds,volume", [(0, 0.03), (3, 0.03), (float("nan"), 0.03), (1, 1), (1, float("inf"))]
)
def test_tone_bounds(seconds, volume):
    with pytest.raises(ValueError):
        tone(seconds, volume)


def test_signal_content_free_and_quiet():
    report = inspect_signal(tone())
    assert report["signal_detected"]
    assert 0 < report["peak_full_scale"] <= 0.031
    assert report["duration_seconds"] == 0.5
    assert not report["speech_quality_verified"]
    quiet = inspect_signal(encode_wav(bytes(3200), 16000))
    assert not quiet["signal_detected"]
    assert quiet["rms_dbfs"] is None


def test_microphone_and_speaker_are_independent_of_provider_config():
    class ToneCapture(MockCapture):
        def record(self, release, cancel, seconds):
            return tone()

    validator = Validator(
        {"JARVIS_AI_URL": "bad"},
        capture=ToneCapture(),
        playback=MockPlayback(),
        consent=Consent(True, True),
    )
    for stage in ("microphone", "speaker"):
        report = validator.run(stage)
        assert report["outcome"] == "passed"
        assert report["effects"]["network"] == "not_requested"
        assert not report["audible_confirmed"]
        assert report["audio_mode"] == "injected_simulation"


@pytest.mark.parametrize("seconds", [0, 6, float("nan")])
def test_capture_duration_rejected_before_device(seconds):
    report = Validator({}, consent=Consent(microphone=True), seconds=seconds).run("microphone")
    assert report["outcome"] == "failed"
    assert report["effects"]["microphone"] == "not_requested"


def test_cancelled_before_effects():
    cancel = Cancellation()
    cancel.cancel()
    report = Validator({}, cancel=cancel, consent=Consent(True, True, True)).run("interaction")
    assert report["outcome"] == "cancelled"
    assert set(report["effects"].values()) == {"not_requested"}


@pytest.mark.parametrize("language", ["en", "de"])
def test_local_tls_provider_stages(monkeypatch, language):
    with MockProviderServer("") as server:
        settings = server.settings()
        settings["JARVIS_VOICE_LANGUAGE"] = language
        for key in ("SSL_CERT_FILE", "NO_PROXY"):
            monkeypatch.setenv(key, settings[key])
        validator = Validator(settings, consent=Consent(network=True))
        for stage in ("stt", "chat", "tts"):
            report = validator.run(stage)
            assert report["outcome"] == "passed", report
            assert report["details"]["http_contract_passed"]
            assert not report["details"]["speech_or_language_quality_verified"]
            assert report["effects"]["microphone"] == "not_requested"
            assert report["effects"]["playback"] == "not_requested"
            assert "synthetic-test-key" not in json.dumps(report)
            assert "reply_text" not in report["details"]
        assert server.calls == ["STT", "AI", "TTS"]


@pytest.mark.parametrize("language,text", [("en", "Open YouTube."), ("de", "Öffne Notepad.")])
def test_interaction_fake_devices_real_local_tls(monkeypatch, language, text):
    with MockProviderServer(text) as server:
        settings = server.settings()
        settings["JARVIS_VOICE_LANGUAGE"] = language
        for key in ("SSL_CERT_FILE", "NO_PROXY"):
            monkeypatch.setenv(key, settings[key])
        report = Validator(
            settings,
            capture=MockCapture(),
            playback=MockPlayback(),
            consent=Consent(True, True, True),
        ).run("interaction")
        assert report["outcome"] == "passed", report
        assert report["effects"]["actions"] == "mock_execution"
        assert "recognized_text" not in report["details"]
        assert not report["representative_hardware_verified"]


def test_cli_blocked_is_sanitized(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["jarvis", "--validate", "stt"])
    assert main() == 2
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "consent_network_required"


def test_cli_synthetic_speaker(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv", ["jarvis", "--validate", "speaker", "--mock-audio", "--allow-playback"]
    )
    assert main() == 0
    assert not json.loads(capsys.readouterr().out)["audible_confirmed"]


def test_benchmark_bounds():
    for duration in (0, 11, float("nan")):
        with pytest.raises(ValueError):
            benchmark(duration)


@pytest.mark.parametrize("stage,role", [("stt", "STT"), ("chat", "AI"), ("tts", "TTS")])
def test_provider_errors_sanitized_and_worker_reaped(monkeypatch, stage, role):
    import multiprocessing

    with MockProviderServer(fault=(role, "auth")) as server:
        settings = server.settings()
        monkeypatch.setenv("SSL_CERT_FILE", settings["SSL_CERT_FILE"])
        monkeypatch.setenv("NO_PROXY", settings["NO_PROXY"])
        report = Validator(settings, consent=Consent(network=True)).run(stage)
        assert report["outcome"] == "failed"
        assert report["error"]["http_status"] == 401
        assert "synthetic-test-key" not in json.dumps(report)
        assert "https://" not in json.dumps(report)
        assert not multiprocessing.active_children()


def test_silent_capture_completed_without_upload():
    class QuietCapture(MockCapture):
        def record(self, release, cancel, seconds):
            return encode_wav(bytes(3200), 16000)

    report = Validator({}, capture=QuietCapture(), consent=Consent(microphone=True)).run(
        "microphone"
    )
    assert report["outcome"] == "failed"
    assert report["error"]["code"] == "insufficient_signal"
    assert report["effects"]["microphone"] == "capture_completed"
    assert report["effects"]["network"] == "not_requested"


def test_unsupported_audio_sanitized():
    class BrokenCapture(MockCapture):
        def record(self, release, cancel, seconds):
            return b"private unsupported input"

    report = Validator({}, capture=BrokenCapture(), consent=Consent(microphone=True)).run(
        "microphone"
    )
    assert report["outcome"] == "failed"
    assert "private" not in json.dumps(report)


def test_devices_offline_no_streams_or_provider_config(monkeypatch):
    from types import SimpleNamespace

    fake = SimpleNamespace(query_devices=lambda: [], default=SimpleNamespace(device=(-1, -1)))
    monkeypatch.setattr("jarvis.validation.runner.audio_backend", lambda: fake)
    report = Validator({"JARVIS_STT_URL": "invalid"}).run("devices")
    assert report["outcome"] == "passed"
    assert report["details"]["streams_opened"] == 0


def test_benchmark_finite_no_providers(monkeypatch):
    monkeypatch.setenv("JARVIS_AI_URL", "https://must-not-call.invalid")
    report = benchmark(1)
    assert report["exit_code"] == 0
    assert not report["network_requested"]
    assert not report["microphone_activated"]
    assert not report["cold_cache_verified"]
