"""Optional read-only authenticated HTTP snapshot channel for ORBIT."""

import hmac
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from jarvis.core.event_bus import EventBus
from jarvis.integration.protocol import LEGACY_EVENT_TYPES


class EventServer:
    def __init__(self, bus: EventBus, token: str, port: int = 0) -> None:
        if len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
            raise ValueError("Use a random ASCII token of at least 32 characters")

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
                self.connection.settimeout(2)

        self._server = HTTPServer(("127.0.0.1", port), Handler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return int(self._server.server_port)

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        if self._thread.is_alive():
            self._server.shutdown()
            self._thread.join(timeout=3)
        self._server.server_close()
