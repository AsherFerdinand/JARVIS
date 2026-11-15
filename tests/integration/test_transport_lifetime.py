"""Real local TLS and disposable workers; no external service or paid API."""

import multiprocessing as mp
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from jarvis.core.cancellation import Cancellation, Cancelled
from jarvis.intelligence.errors import ProviderError
from jarvis.intelligence.transport import Call, ProcessTransport


@pytest.fixture
def local_tls(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    entered, stop = threading.Event(), threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            entered.set()
            try:
                if self.path == "/headers":
                    stop.wait(5)
                    return
                self.send_response(200)
                self.send_header("Content-Length", "20" if self.path == "/drip" else "2")
                self.end_headers()
                if self.path == "/drip":
                    for _ in range(20):
                        self.wfile.write(b"x")
                        self.wfile.flush()
                        if stop.wait(0.15):
                            break
                else:
                    self.wfile.write(b"ok")
            except (OSError, ssl.SSLError):
                pass

        def log_message(self, *args):
            pass

    root = Path(__file__).resolve().parents[1] / "fixtures"
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(root / "localhost-cert.pem", root / "localhost-key.pem")
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"https://127.0.0.1:{server.server_port}", str(root / "localhost-cert.pem"), entered
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
        thread.join(3)


def request(base, cert, path):
    return Call(base + path, {}, b"{}", connection_timeout=2, response_timeout=2, ca_file=cert)


def test_real_tls_worker_and_certificate_validation(local_tls):
    base, cert, _ = local_tls
    before = {p.pid for p in mp.active_children()}
    assert ProcessTransport().request(request(base, cert, "/ok"), Cancellation(), 5) == b"ok"
    assert {p.pid for p in mp.active_children()} == before
    with pytest.raises(ProviderError) as error:
        ProcessTransport().request(Call(base + "/ok", {}, b"{}"), Cancellation(), 5)
    assert error.value.code == "tls_error"


@pytest.mark.parametrize("path", ["/headers", "/drip"])
def test_total_deadline_bounds_headers_and_slow_drip(local_tls, path):
    base, cert, _ = local_tls
    started = time.monotonic()
    with pytest.raises(ProviderError) as error:
        ProcessTransport().request(request(base, cert, path), Cancellation(), 1)
    assert error.value.code == "request_deadline"
    assert time.monotonic() - started < 3
    assert not any(p.name == "jarvis-provider" for p in mp.active_children())


def test_cancel_terminates_active_local_worker_and_recovers(local_tls):
    base, cert, entered = local_tls
    token = Cancellation()
    results = []

    def run():
        try:
            ProcessTransport().request(request(base, cert, "/headers"), token, 10)
        except Cancelled:
            results.append("cancelled")

    thread = threading.Thread(target=run)
    thread.start()
    assert entered.wait(5)
    token.cancel()
    thread.join(3)
    assert results == ["cancelled"]
    assert not thread.is_alive()
    assert not any(p.name == "jarvis-provider" for p in mp.active_children())
    assert ProcessTransport().request(request(base, cert, "/ok"), Cancellation(), 5) == b"ok"


def test_response_timeout_is_distinct_from_total_deadline(local_tls):
    base, cert, _ = local_tls
    call = Call(
        base + "/headers", {}, b"{}", connection_timeout=2, response_timeout=0.2, ca_file=cert
    )
    with pytest.raises(ProviderError) as error:
        ProcessTransport().request(call, Cancellation(), 5)
    assert error.value.code == "response_timeout"


def test_controller_shutdown_during_real_network_request(local_tls):
    from test_voice import make_controller

    from jarvis.speech.session import State

    base, cert, entered = local_tls

    class NetworkSTT:
        def transcribe(self, audio, cancel):
            ProcessTransport().request(request(base, cert, "/headers"), cancel, 10)
            return "open youtube"

    controller = make_controller(stt=NetworkSTT())
    controller.start()
    assert entered.wait(5)
    started = time.monotonic()
    controller.close()
    assert time.monotonic() - started < 2.5
    assert controller.wait(3).state.current == State.CANCELLED
    assert not controller.assistant.executor.calls
    assert not any(p.name == "jarvis-provider" for p in mp.active_children())
