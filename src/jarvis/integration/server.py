"""Optional read-only authenticated HTTP snapshot channel for ORBIT."""

import hmac
import io
import json
import logging
import socket
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event as ThreadEvent
from threading import Lock, Thread

from jarvis.core.event_bus import EventBus
from jarvis.integration.protocol import LEGACY_EVENT_TYPES


class HeaderReader(io.BufferedIOBase):
    """Bounded GET headers, independent of cross-thread Winsock shutdown wakeups."""

    def __init__(
        self, connection: socket.socket, closing: ThreadEvent, deadline_seconds: float = 2
    ) -> None:
        super().__init__()
        self.connection, self.closing = connection, closing
        self.deadline = time.monotonic() + deadline_seconds
        self.buffer = bytearray()
        self.received = 0

    def readline(self, size: int = -1) -> bytes:
        if size == 0:
            return b""
        limit = 65537 if size < 0 else min(size, 65537)
        while True:
            if self.closing.is_set():
                return b""
            if time.monotonic() >= self.deadline:
                raise TimeoutError("Header deadline exceeded")
            end = self.buffer.find(b"\n")
            if end >= 0 or len(self.buffer) >= limit:
                length = min(end + 1, limit) if end >= 0 else limit
                result = bytes(self.buffer[:length])
                del self.buffer[:length]
                return result
            try:
                chunk = self.connection.recv(4096)
            except TimeoutError:
                continue
            if not chunk:
                result = bytes(self.buffer)
                self.buffer.clear()
                return result
            self.received += len(chunk)
            if self.received > 65536:
                raise ValueError("Header size exceeded")
            self.buffer.extend(chunk)


class LocalServer(HTTPServer):
    def __init__(self, address: tuple[str, int], handler: type[BaseHTTPRequestHandler]) -> None:
        self._connection_lock = Lock()
        self._closing = ThreadEvent()
        self._active: socket.socket | None = None
        super().__init__(address, handler)

    def get_request(self) -> tuple[socket.socket, tuple[str, int]]:
        connection, address = super().get_request()
        with self._connection_lock:
            if self._closing.is_set():
                connection.close()
                raise OSError("Server stopping")
            self._active = connection
        return connection, address

    def shutdown_request(self, request: socket.socket | tuple[bytes, socket.socket]) -> None:
        if not isinstance(request, socket.socket):
            raise TypeError("TCP socket required")
        try:
            super().shutdown_request(request)
        finally:
            with self._connection_lock:
                if self._active is request:
                    self._active = None

    def handle_error(self, request: object, client_address: object) -> None:
        logging.getLogger("jarvis").debug("Event client disconnected")

    def interrupt_client(self) -> None:
        self._closing.set()
        with self._connection_lock:
            connection = self._active
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                return  # Client already closed; server shutdown still follows.


class EventServer:
    def __init__(self, bus: EventBus, token: str, port: int = 0) -> None:
        if len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
            raise ValueError("Use a random ASCII token of at least 32 characters")

        server_closing = ThreadEvent()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                supplied = self.headers.get("Authorization", "")
                if not hmac.compare_digest(supplied.encode(), f"Bearer {token}".encode()):
                    self.send_error(401)
                    return
                if self.path not in {"/v1/events", "/v1/voice-events"}:
                    self.send_error(404)
                    return
                values = [e.to_dict() for e in bus.snapshot()]
                if self.path == "/v1/events":
                    values = [
                        {
                            k: v
                            for k, v in e.items()
                            if k not in {"session_id", "recognized_text", "error_info"}
                        }
                        for e in values
                        if e["event"] in LEGACY_EVENT_TYPES
                    ]
                body = json.dumps({"version": 1, "events": values}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                pass

            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(0.05)
                self.rfile.close()
                self.rfile = HeaderReader(self.connection, server_closing)

        self._server = LocalServer(("127.0.0.1", port), Handler)
        self._server._closing = server_closing
        self._thread = Thread(target=self._server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return int(self._server.server_port)

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        self._server.interrupt_client()
        if self._thread.is_alive():
            self._server.shutdown()
            self._thread.join(timeout=3)
        self._server.server_close()
