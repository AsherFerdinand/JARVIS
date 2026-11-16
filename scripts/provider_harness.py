"""Offline end-to-end TLS provider harness, shared by pytest and extracted-executable CI."""

import argparse
import json
import os
import socket
import ssl
import subprocess
import threading
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from jarvis.speech.audio import decode_wav, synthetic_wav


def require(condition: bool) -> None:
    if not condition:
        raise ValueError("Synthetic provider contract mismatch")


class MockProviderServer:
    def __init__(
        self, transcript: str = "Open YouTube.", fault: tuple[str, str] | None = None
    ) -> None:
        self.transcript, self.fault = transcript, fault
        self.calls: list[str] = []
        self.fields: list[dict[str, object]] = []
        self.entered, self.stop = threading.Event(), threading.Event()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                role = {
                    "/v1/audio/transcriptions": "STT",
                    "/v1/chat/completions": "AI",
                    "/v1/audio/speech": "TTS",
                }.get(self.path)
                if role is None:
                    self.send_error(404)
                    return
                owner.calls.append(role)
                owner.entered.set()
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4_010_000:
                    self.send_error(413)
                    return
                payload = self.rfile.read(length)
                if self.headers.get("Authorization") != "Bearer synthetic-test-key":
                    self.send_error(401)
                    return
                fault = owner.fault[1] if owner.fault and owner.fault[0] == role else None
                if fault in {"auth", "rate", "server"}:
                    self.send_error({"auth": 401, "rate": 429, "server": 503}[fault])
                    return
                if fault == "slow":
                    owner.stop.wait(8)
                    return
                if fault == "disconnect":
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
                try:
                    if role == "STT":
                        content_type = self.headers["Content-Type"]
                        if not content_type.startswith("multipart/form-data;"):
                            raise ValueError("Expected multipart")
                        message = BytesParser(policy=policy.default).parsebytes(
                            f"Content-Type: {content_type}\r\n\r\n".encode() + payload
                        )
                        parts = {
                            part.get_param("name", header="content-disposition"): part
                            for part in message.iter_parts()
                        }
                        decode_wav(parts["file"].get_payload(decode=True), require_sound=True)
                        require(parts["file"].get_filename() == "speech.wav")
                        require(parts["model"].get_payload() == "fixture-model")
                        response_format = parts["response_format"].get_payload()
                        owner.fields.append(
                            {
                                "role": role,
                                "language_present": "language" in parts,
                                "format": response_format,
                            }
                        )
                        body = (
                            owner.transcript.encode()
                            if response_format == "text"
                            else json.dumps({"text": owner.transcript}).encode()
                        )
                    else:
                        values = json.loads(payload)
                        require(values["model"] == "fixture-model")
                        if role == "AI":
                            require(values["messages"][-1]["role"] == "user")
                            require("tools" not in values)
                            owner.fields.append(
                                {"role": "AI", "instruction_role": values["messages"][0]["role"]}
                            )
                            body = json.dumps(
                                {
                                    "choices": [{"message": {"content": "Synthetic explanation."}}],
                                    "usage": {"total_tokens": 7},
                                }
                            ).encode()
                        else:
                            require(values["voice"] == "fixture-voice")
                            require(values["response_format"] == "wav")
                            require(isinstance(values["input"], str))
                            owner.fields.append({"role": role, "speed_present": "speed" in values})
                            body = synthetic_wav()
                except (ValueError, KeyError, TypeError, AssertionError):
                    self.send_error(400)
                    return
                if fault == "malformed":
                    body = b"invalid synthetic data"
                try:
                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "audio/wav" if role == "TTS" else "application/json"
                    )
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (OSError, ssl.SSLError):
                    pass

            def log_message(self, *args: object) -> None:
                pass

        root = Path(__file__).resolve().parents[1] / "tests/fixtures"
        self.cert = root / "localhost-cert.pem"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = False
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.cert, root / "localhost-key.pem")
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> "MockProviderServer":
        self.thread.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)

    def settings(self) -> dict[str, str]:
        base = f"https://127.0.0.1:{self.server.server_port}"
        result = {
            "SSL_CERT_FILE": str(self.cert),
            "NO_PROXY": "localhost,127.0.0.1",
            "no_proxy": "localhost,127.0.0.1",
            "JARVIS_TTS_VOICE": "fixture-voice",
        }
        for role, path in [
            ("STT", "audio/transcriptions"),
            ("TTS", "audio/speech"),
            ("AI", "chat/completions"),
        ]:
            result.update(
                {
                    f"JARVIS_{role}_URL": f"{base}/v1/{path}",
                    f"JARVIS_{role}_KEY": "synthetic-test-key",
                    f"JARVIS_{role}_MODEL": "fixture-model",
                    f"JARVIS_{role}_DEADLINE": "6",
                }
            )
        return result


def executable_pipeline(executable: Path, directory: Path) -> dict[str, object]:
    audio = directory / "synthetic.wav"
    audio.write_bytes(synthetic_wav())
    outcomes = []
    for transcript, expected in [
        ("Open YouTube.", ["STT", "TTS"]),
        ("Explain regenerative braking.", ["STT", "AI", "TTS"]),
    ]:
        with MockProviderServer(transcript) as server:
            environment = {
                key: value
                for key, value in os.environ.items()
                if not key.startswith("JARVIS_")
                and key not in {"VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME", "UV_PROJECT_ENVIRONMENT"}
            }
            environment.update(server.settings())
            if os.name == "nt":
                system = Path(os.environ.get("SystemRoot", r"C:\Windows"))
                environment["PATH"] = str(system / "System32") + os.pathsep + str(system)
            run = subprocess.run(  # noqa: S603 -- own extracted executable, fixed test arguments
                [
                    str(executable),
                    "--mock",
                    "--voice-file",
                    str(audio),  # noqa: S603
                    "--mock-audio",
                    "--diagnostics",
                ],
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if run.returncode != 0:
                raise RuntimeError("Extracted HTTP voice pipeline failed")
            result = json.loads(run.stdout.splitlines()[-1])
            if result["state"] != "completed" or server.calls != expected:
                raise RuntimeError("Incomplete extracted provider pipeline")
            if result["active_request_workers"] != 0:
                raise RuntimeError("Extracted provider worker remained active")
            outcomes.append(
                {
                    "providers": server.calls,
                    "state": result["state"],
                    "memory": result["process"],
                    "python_peak_bytes": result["python_peak_bytes"],
                }
            )
    audio.unlink()
    return {"pipeline_cases": outcomes, "paid_calls": 0, "audio_devices_opened": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    arguments = parser.parse_args()
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        print(
            json.dumps(executable_pipeline(arguments.executable.resolve(), Path(folder)), indent=2)
        )
