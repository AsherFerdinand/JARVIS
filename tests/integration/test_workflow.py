import json
import subprocess
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from jarvis.actions.windows import MockExecutor
from jarvis.config import Config
from jarvis.core.lifecycle import Assistant
from jarvis.integration.server import EventServer


def test_cli():
    result = subprocess.run(
        [sys.executable, "-m", "jarvis.main", "--mock", "--command", "status"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "JARVIS ready"


def test_event_channel_auth_and_restart():
    assistant = Assistant(Config(), MockExecutor())
    token = "a" * 48
    for _ in range(2):
        server = EventServer(assistant.events, token)
        server.start()
        try:
            url = f"http://127.0.0.1:{server.port}/v1/events"
            with pytest.raises(HTTPError) as error:
                urlopen(url, timeout=3)
            assert error.value.code == 401
            assistant.handle("status")
            request = Request(url, headers={"Authorization": f"Bearer {token}"})
            with urlopen(request, timeout=3) as response:
                body = json.load(response)
                assert response.headers["Cache-Control"] == "no-store"
            assert body["version"] == 1
            assert body["events"][-1]["event"] == "assistant.idle"
        finally:
            server.close()


def test_short_token_rejected():
    with pytest.raises(ValueError):
        EventServer(Assistant(Config(), MockExecutor()).events, "short")


@pytest.mark.parametrize("command,code", [("unknown command", 1), ("exit", 0)])
def test_cli_exit_status(command, code):
    result = subprocess.run(
        [sys.executable, "-m", "jarvis.main", "--mock", "--command", command],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == code
    assert "Traceback" not in result.stderr


def test_cli_eof_and_interactive_exit():
    for commands in ["", "status\nexit\nopen youtube\n"]:
        result = subprocess.run(
            [sys.executable, "-m", "jarvis.main", "--mock"],
            input=commands,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "Website opened" not in result.stdout


def test_cli_partial_provider_is_private(monkeypatch):
    monkeypatch.setenv("JARVIS_AI_KEY", "private-test-credential")
    monkeypatch.delenv("JARVIS_AI_URL", raising=False)
    monkeypatch.delenv("JARVIS_AI_MODEL", raising=False)
    result = subprocess.run(
        [sys.executable, "-m", "jarvis.main", "--mock", "--command", "status"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert "private-test-credential" not in result.stdout + result.stderr
