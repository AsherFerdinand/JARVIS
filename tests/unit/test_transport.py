import io
import time
from urllib.error import HTTPError, URLError

import pytest

from jarvis.core.cancellation import Cancellation, Cancelled
from jarvis.intelligence.errors import ProviderError
from jarvis.intelligence.transport import Call, Outcome, ProcessTransport, exchange


def call(method="POST", **kwargs):
    return Call("https://example.invalid/test", {}, b"{}", method=method, **kwargs)


@pytest.mark.parametrize(
    "status,code,transient",
    [
        (401, "authentication_failed", False),
        (403, "authentication_failed", False),
        (429, "rate_limited", True),
        (500, "server_error", True),
        (503, "server_error", True),
        (400, "http_error", False),
        (302, "redirect_denied", False),
    ],
)
def test_http_errors_are_sanitized(status, code, transient):
    class Broken:
        def open(self, *args, **kwargs):
            raise HTTPError(
                "https://private.invalid?key=secret",
                status,
                "private message",
                {"Retry-After": "1"},
                io.BytesIO(b"private payload"),
            )

    result = exchange(call(), Broken())
    assert (result.code, result.status, result.transient) == (code, status, transient)
    assert not result.body
    assert "secret" not in repr(result)


def test_connection_timeout_and_network_classification():
    class Broken:
        def __init__(self, error):
            self.error = error

        def open(self, *args, **kwargs):
            raise self.error

    assert exchange(call(), Broken(TimeoutError())).code == "connection_timeout"
    assert exchange(call(), Broken(URLError("offline"))).code == "network_unavailable"


def test_partial_and_response_timeout():
    class Partial(io.BytesIO):
        headers = {"Content-Length": "10"}

    class Fake:
        def open(self, *args, **kwargs):
            return Partial(b"abc")

    assert exchange(call(), Fake()).code == "partial_response"

    class Slow(Partial):
        def read1(self, size):
            raise TimeoutError()

    class FakeSlow:
        def open(self, *args, **kwargs):
            return Slow(b"abc")

    assert exchange(call(), FakeSlow()).code == "response_timeout"


@pytest.mark.parametrize("method,attempts", [("POST", 1), ("GET", 3), ("HEAD", 3)])
def test_only_safe_methods_retry(monkeypatch, method, attempts):
    seen = []

    def failed(self, request, cancel, deadline):
        seen.append(request)
        return Outcome(code="server_error", status=503, transient=True)

    monkeypatch.setattr(ProcessTransport, "_attempt", failed)
    with pytest.raises(ProviderError) as error:
        ProcessTransport().request(call(method), Cancellation(), 3)
    assert len(seen) == attempts
    assert error.value.to_dict()["http_status"] == 503


def test_transient_recovery_and_auth_not_retried(monkeypatch):
    results = iter([Outcome(code="network_unavailable", transient=True), Outcome(body=b"ok")])
    monkeypatch.setattr(ProcessTransport, "_attempt", lambda *args: next(results))
    assert ProcessTransport().request(call("GET"), Cancellation(), 3) == b"ok"
    monkeypatch.setattr(
        ProcessTransport, "_attempt", lambda *args: Outcome(code="authentication_failed")
    )
    with pytest.raises(ProviderError) as error:
        ProcessTransport().request(call("GET"), Cancellation(), 3)
    assert error.value.code == "authentication_failed"


def test_cancel_interrupts_backoff(monkeypatch):
    cancel = Cancellation()

    def failed(*args):
        cancel.cancel()
        return Outcome(code="rate_limited", transient=True)

    monkeypatch.setattr(ProcessTransport, "_attempt", failed)
    started = time.monotonic()
    with pytest.raises(Cancelled):
        ProcessTransport().request(call("GET"), cancel, 3)
    assert time.monotonic() - started < 0.5


def test_capacity_queue_is_deadline_bounded():
    transport = ProcessTransport()
    assert transport._slots.acquire(timeout=1)
    try:
        with pytest.raises(ProviderError) as error:
            transport.request(call(), Cancellation(), 0.05)
        assert error.value.code == "transport_busy"
    finally:
        transport._slots.release()
