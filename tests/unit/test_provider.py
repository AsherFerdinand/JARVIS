import io
import json
from urllib.error import URLError

import pytest

from jarvis.intelligence.provider import OpenAIProvider, ProviderError


class Response(io.BytesIO):
    pass


class Opener:
    def __init__(self, body):
        self.body = body

    def open(self, request, timeout):
        assert timeout == 15
        assert request.get_header("Authorization") == "Bearer test-key"
        return Response(self.body)


def test_structured_response(monkeypatch):
    body = json.dumps(
        {
            "choices": [{"message": {"content": '{"action":"assistant_status"}'}}],
            "usage": {"total_tokens": 8},
        }
    ).encode()
    monkeypatch.setattr("jarvis.intelligence.provider._opener", lambda: Opener(body))
    result = OpenAIProvider(
        "https://api.example/v1/chat/completions", "test", "test-key"
    ).interpret("hi")
    assert result.intent.action == "assistant_status"
    assert result.total_tokens == 8


@pytest.mark.parametrize(
    "body",
    [b"bad", b"{}", b"x" * 65537, b'{"choices":[{"message":{"content":"[]"}}]}'],
    ids=["invalid-json", "missing", "oversize", "wrong-shape"],
)
def test_bad_response(monkeypatch, body):
    monkeypatch.setattr("jarvis.intelligence.provider._opener", lambda: Opener(body))
    with pytest.raises(ProviderError):
        OpenAIProvider("https://api.example/v1/chat/completions", "test", "test-key").interpret(
            "hi"
        )


def test_network_error(monkeypatch):
    class BrokenOpener:
        def open(self, request, timeout):
            raise URLError("unavailable")

    monkeypatch.setattr("jarvis.intelligence.provider._opener", BrokenOpener)
    with pytest.raises(ProviderError):
        OpenAIProvider("https://api.example/v1/chat/completions", "test", "test-key").interpret(
            "hi"
        )


@pytest.mark.parametrize(
    "url", ["http://example.com", "https://user:pass@example.com", "file:///a"]
)
def test_url_restrictions(url):
    with pytest.raises(ValueError):
        OpenAIProvider(url, "test", "test-key")


def test_redirects_rejected():
    from urllib.request import HTTPRedirectHandler, Request

    from jarvis.intelligence.provider import _opener

    handlers = [h for h in _opener().handlers if isinstance(h, HTTPRedirectHandler)]
    assert len(handlers) == 1
    request = Request("https://api.example/v1/chat/completions")
    assert (
        handlers[0].redirect_request(request, None, 302, "redirect", {}, "https://other.example")
        is None
    )


def test_usage_shape_rejected(monkeypatch):
    body = json.dumps(
        {"choices": [{"message": {"content": '{"action":"assistant_status"}'}}], "usage": []}
    ).encode()
    monkeypatch.setattr("jarvis.intelligence.provider._opener", lambda: Opener(body))
    with pytest.raises(ProviderError):
        OpenAIProvider("https://api.example/v1/chat/completions", "test", "test-key").interpret(
            "hi"
        )
