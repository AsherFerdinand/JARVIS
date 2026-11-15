"""Standard-library HTTPS in a disposable child: bounded DNS/headers/body lifetime.

Cancellation terminates the local worker, not the remote operation. POSTs are never retried.
No child exists while idle. Frozen entry points must call multiprocessing.freeze_support().
"""

import http.client
import multiprocessing as mp
import random
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from multiprocessing.connection import Connection
from threading import BoundedSemaphore
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, OpenerDirector, Request, build_opener

from jarvis.core.cancellation import Cancellation
from jarvis.intelligence.errors import ProviderError


@dataclass(frozen=True)
class Call:
    url: str = field(repr=False)
    headers: dict[str, str] = field(repr=False)
    payload: bytes | None = field(repr=False)
    method: str = "POST"
    connection_timeout: float = 10
    response_timeout: float = 15
    limit: int = 65536
    # Tests may trust their generated local certificate; never disables TLS verification.
    ca_file: str | None = None

    def __post_init__(self) -> None:
        parsed = urlsplit(self.url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("HTTPS endpoint without URL credentials required")
        if self.method not in {"POST", "GET", "HEAD"}:
            raise ValueError("Unsupported method")
        if not (
            0 < self.connection_timeout <= 120
            and 0 < self.response_timeout <= 120
            and 0 < self.limit <= 4_000_000
        ):
            raise ValueError("Invalid transport bounds")


@dataclass
class Outcome:
    body: bytes = field(default=b"", repr=False)
    code: str | None = None
    status: int | None = None
    transient: bool = False
    retry_after: float | None = None
    resources: dict[str, int | float | None] | None = None


def _opener(
    response_timeout: float, connected: Callable[[], None], ca_file: str | None = None
) -> OpenerDirector:
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
            return None

    class HTTPSConnection(http.client.HTTPSConnection):
        def connect(self) -> None:
            super().connect()
            connected()
            if self.sock is not None:
                self.sock.settimeout(response_timeout)

    class Handler(HTTPSHandler):
        def https_open(self, req):  # type: ignore[no-untyped-def]
            return self.do_open(
                HTTPSConnection, req, context=ssl.create_default_context(cafile=ca_file)
            )

    return build_opener(NoRedirect(), Handler())


def exchange(call: Call, opener: OpenerDirector | None = None) -> Outcome:
    """One wire attempt. Production calls only inside a deadline-supervised child."""
    phase = "connection"

    def connected() -> None:
        nonlocal phase
        phase = "response"

    try:
        client = opener or _opener(call.response_timeout, connected, call.ca_file)
        request = Request(  # noqa: S310 -- Call validates HTTPS
            call.url,
            data=call.payload,
            headers=call.headers,
            method=call.method,
        )
        with client.open(request, timeout=call.connection_timeout) as response:
            phase = "response"
            expected = (
                response.headers.get("Content-Length") if hasattr(response, "headers") else None
            )
            length = int(expected) if expected is not None else None
            if length is not None and not 0 <= length <= call.limit:
                return Outcome(code="response_too_large")
            chunks: list[bytes] = []
            size = 0
            while True:
                # read1 avoids waiting to fill a large chunk; parent enforces the total deadline.
                read = getattr(response, "read1", response.read)
                chunk = read(min(65536, call.limit + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > call.limit:
                    return Outcome(code="response_too_large")
            if length is not None and size != length and call.method != "HEAD":
                return Outcome(code="partial_response", transient=True)
            return Outcome(body=b"".join(chunks))
    except HTTPError as exc:
        status = exc.code
        retry_after = None
        try:
            candidate = float(exc.headers.get("Retry-After", ""))
            if 0 <= candidate <= 30:
                retry_after = candidate
        except (ValueError, TypeError, AttributeError):
            pass
        finally:
            exc.close()
        code = (
            "authentication_failed"
            if status in {401, 403}
            else "rate_limited"
            if status == 429
            else "server_error"
            if 500 <= status <= 599
            else "redirect_denied"
            if 300 <= status <= 399
            else "http_error"
        )
        return Outcome(
            code=code,
            status=status,
            transient=status == 429 or 500 <= status <= 599,
            retry_after=retry_after,
        )
    except TimeoutError:
        return Outcome(code=f"{phase}_timeout", transient=True)
    except URLError as exc:
        if isinstance(exc.reason, ssl.SSLError):
            return Outcome(code="tls_error")
        if isinstance(exc.reason, TimeoutError):
            return Outcome(code=f"{phase}_timeout", transient=True)
        return Outcome(code="network_unavailable", transient=True)
    except ssl.SSLError:
        return Outcome(code="tls_error")
    except (http.client.IncompleteRead, http.client.RemoteDisconnected):
        return Outcome(code="partial_response", transient=True)
    except (OSError, http.client.HTTPException):
        return Outcome(code="network_unavailable", transient=True)
    except (ValueError, TypeError, OverflowError):
        return Outcome(code="malformed_response")


def _worker(sender: Connection, call: Call | None) -> None:
    try:
        if call is None:
            from jarvis.diagnostics.resources import process_resources

            try:
                resources = process_resources()
            except OSError:
                resources = None
            sender.send(Outcome(body=b"ready", resources=resources))
        else:
            sender.send(exchange(call))
    except Exception:
        # Do not send exception strings, request headers or provider payloads.
        try:
            sender.send(Outcome(code="transport_failure"))
        except (OSError, EOFError):
            pass
    finally:
        sender.close()


class Transport(Protocol):
    def request(self, call: Call, cancel: Cancellation, total_timeout: float) -> bytes: ...


class ProcessTransport:
    _slots = BoundedSemaphore(1)

    def _attempt(self, call: Call | None, cancel: Cancellation, deadline: float) -> Outcome:
        context = mp.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(
            target=_worker, args=(sender, call), daemon=True, name="jarvis-provider"
        )
        try:
            cancel.check()
            if time.monotonic() >= deadline:
                return Outcome(code="request_deadline", transient=True)
            process.start()
            sender.close()
            while True:
                cancel.check()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return Outcome(code="request_deadline", transient=True)
                if receiver.poll(min(0.05, remaining)):
                    result: Outcome = receiver.recv()
                    cancel.check()
                    return result
                if not process.is_alive():
                    return Outcome(code="transport_failure")
        except (OSError, EOFError, ValueError):
            return Outcome(code="transport_failure")
        finally:
            sender.close()
            receiver.close()
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                process.join(0.25)
                if process.is_alive():
                    process.kill()
                    process.join(0.25)
                process.close()

    def request(self, call: Call, cancel: Cancellation, total_timeout: float = 30) -> bytes:
        if not 0 < total_timeout <= 120:
            raise ValueError("Invalid request deadline")
        deadline = time.monotonic() + total_timeout
        while not self._slots.acquire(timeout=min(0.05, max(0, deadline - time.monotonic()))):
            cancel.check()
            if time.monotonic() >= deadline:
                raise ProviderError(
                    "Provider capacity deadline", code="transport_busy", transient=True
                )
        try:
            cancel.check()
            return self._request(call, cancel, deadline)
        finally:
            self._slots.release()

    def _request(self, call: Call, cancel: Cancellation, deadline: float) -> bytes:
        for attempt in range(3):
            result = self._attempt(call, cancel, deadline)
            if result.code is None:
                return result.body
            # A POST can incur charges/effects even when the response is lost. Never replay it.
            if call.method not in {"GET", "HEAD"} or not result.transient or attempt == 2:
                break
            delay = min(2.0, 0.2 * 2**attempt + random.uniform(0, 0.1))  # noqa: S311
            if result.retry_after is not None:
                if result.retry_after > 2:
                    break
                delay = max(delay, result.retry_after)
            if time.monotonic() + delay >= deadline:
                break
            if cancel.event.wait(delay):
                cancel.check()
        raise ProviderError(
            "Provider request failed",
            code=result.code or "transport_failure",
            status=result.status,
            transient=result.transient,
            retry_after=result.retry_after,
        )

    def probe(self) -> dict[str, int | float | None] | None:
        deadline = time.monotonic() + 10
        if not self._slots.acquire(timeout=10):
            raise ProviderError("Provider runtime busy", code="transport_busy")
        try:
            result = self._attempt(None, Cancellation(), deadline)
            if result.code is not None or result.body != b"ready":
                raise ProviderError("Provider worker unavailable", code="transport_failure")
            return result.resources
        finally:
            self._slots.release()


def unwrap(outcome: Outcome) -> bytes:
    if outcome.code is not None:
        raise ProviderError(
            "Provider request failed",
            code=outcome.code,
            status=outcome.status,
            transient=outcome.transient,
            retry_after=outcome.retry_after,
        )
    return outcome.body


@dataclass(frozen=True)
class Endpoint:
    url: str
    key: str = field(repr=False)
    model: str
    timeout: float = 15
    connection_timeout: float = 10
    total_timeout: float = 30
    transport: Transport | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        # Validate URL and limits without starting transport or importing audio.
        Call(
            self.url,
            {},
            None,
            connection_timeout=self.connection_timeout,
            response_timeout=self.timeout,
        )
        if not self.key or not self.model or not 0 < self.total_timeout <= 120:
            raise ValueError("Cloud endpoint requires credentials, model and deadline")
        if any(c in self.model for c in '\r\n"'):
            raise ValueError("Invalid model identifier")

    def post(
        self, payload: bytes, content_type: str, cancel: Cancellation, limit: int = 65536
    ) -> bytes:
        cancel.check()
        if len(payload) > 4_010_000:
            raise ProviderError("Request exceeded size limit", code="request_too_large")
        call = Call(
            self.url,
            {"Authorization": f"Bearer {self.key}", "Content-Type": content_type},
            payload,
            connection_timeout=min(self.connection_timeout, self.timeout),
            response_timeout=self.timeout,
            limit=limit,
        )
        body = (self.transport or ProcessTransport()).request(call, cancel, self.total_timeout)
        cancel.check()
        return body
