import json
import subprocess
import sys

import pytest

from jarvis.intelligence.preflight import preflight


def settings(role="STT"):
    path = "audio/transcriptions" if role == "STT" else "audio/speech"
    return {
        f"JARVIS_{role}_URL": f"https://api.example/v1/{path}",
        f"JARVIS_{role}_MODEL": "chosen-model",
        f"JARVIS_{role}_KEY": "private-placeholder",
        "JARVIS_TTS_VOICE": "chosen-voice",
    }


@pytest.mark.parametrize(
    "key,value,code",
    [
        ("URL", "http://private-host", "invalid_url"),
        ("URL", "https://u:private@host", "invalid_url"),
        ("MODEL", "", "missing_model"),
        ("KEY", "", "missing_credential"),
        ("PROFILE", "unknown", "invalid_capability_profile"),
        ("RESPONSE_FORMAT", "srt", "unsupported_transcription_format"),
        ("DEADLINE", "nan", "invalid_timeout"),
        ("TIMEOUT", "0", "invalid_timeout"),
        ("LANGUAGE_HINT", "maybe", "invalid_capability_profile"),
    ],
)
def test_offline_configuration_errors(key, value, code, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("Offline preflight used transport")

    monkeypatch.setattr("jarvis.intelligence.transport.ProcessTransport.request", no_network)
    data = settings()
    data[f"JARVIS_STT_{key}"] = value
    result = preflight(data)
    assert code in result["providers"]["STT"]["errors"]
    assert not result["providers"]["STT"]["valid"]
    assert result["network_requests"] == 0
    assert not result["live_verified"]
    assert "private-placeholder" not in json.dumps(result)


@pytest.mark.parametrize(
    "data,code",
    [
        ({"JARVIS_VOICE_LANGUAGE": "fr"}, "invalid_language"),
        ({"JARVIS_TTS_FORMAT": "mp3"}, "unsupported_audio_format"),
        ({"JARVIS_TTS_RATE": "5"}, "invalid_speaking_rate"),
        (
            {"JARVIS_TTS_PROFILE": "compatible", "JARVIS_TTS_RATE": "1.2"},
            "speaking_rate_not_supported",
        ),
        ({"JARVIS_AI_SCHEMA": "responses"}, "unsupported_chat_schema"),
    ],
)
def test_unsupported_capabilities(data, code):
    report = preflight(data)
    assert not report["valid_configured_providers"]
    assert any(code in value["errors"] for value in report["providers"].values())


def test_documented_model_restriction_and_custom_paths():
    data = settings()
    data["JARVIS_STT_MODEL"] = "gpt-4o-transcribe"
    data["JARVIS_STT_RESPONSE_FORMAT"] = "text"
    assert "model_requires_json_transcription" in preflight(data)["providers"]["STT"]["errors"]
    data["JARVIS_STT_RESPONSE_FORMAT"] = "json"
    data["JARVIS_STT_URL"] = "https://api.example/custom/transcriptions"
    report = preflight(data)["providers"]["STT"]
    assert report["valid"]
    assert "custom_path_unverified" in report["warnings"]
    assert "model_and_endpoint_not_live_verified" in report["warnings"]


def test_empty_provider_configuration_keeps_basic_app_usable():
    report = preflight({})
    assert report["valid_configured_providers"]
    assert not report["providers"]["STT"]["configured"]
    assert "missing_credential" in report["providers"]["STT"]["errors"]


def test_preflight_cli_no_backend_import():
    result = subprocess.run(
        [sys.executable, "-m", "jarvis.main", "--provider-preflight"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["network_requests"] == 0


def test_role_capabilities_do_not_claim_unimplemented_optional_fields():
    report = preflight({"JARVIS_TTS_LANGUAGE_HINT": "1"})
    assert "unsupported_optional_capability" in report["providers"]["TTS"]["errors"]
    assert report["providers"]["AI"]["capabilities"] == {
        "chat_completions": True,
        "tool_execution": False,
    }
