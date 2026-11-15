"""Documented OpenAI audio REST formats; endpoints/models supplied explicitly."""

import json
import uuid
from dataclasses import dataclass, field
from urllib.parse import urlparse
from urllib.request import Request

from jarvis.core.cancellation import Cancellation
from jarvis.intelligence.provider import ProviderError, _opener
from jarvis.speech.audio import MAX_AUDIO_BYTES, decode_wav


@dataclass(frozen=True)
class Endpoint:
    url: str
    key: str = field(repr=False)
    model: str
    timeout: float = 15

    def __post_init__(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Cloud endpoint requires HTTPS without URL credentials")
        if not self.key or not self.model or not 0 < self.timeout <= 120:
            raise ValueError("Cloud endpoint requires credentials, model and a bounded timeout")
        if any(c in self.model for c in '\r\n"'):
            raise ValueError("Invalid model identifier")

    def post(
        self, payload: bytes, content_type: str, cancel: Cancellation, limit: int = 65536
    ) -> bytes:
        cancel.check()
        request = Request(  # noqa: S310 -- endpoint is HTTPS-validated
            self.url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.key}",
                "Content-Type": content_type,
            },
        )
        try:
            with _opener().open(request, timeout=self.timeout) as response:
                body: bytes = response.read(limit + 1)
            cancel.check()
            if len(body) > limit:
                raise ProviderError("Cloud response exceeded size limit")
            return body
        except (OSError, ValueError) as exc:
            raise ProviderError("Cloud request failed") from exc


class CloudSTT:
    def __init__(self, endpoint: Endpoint, language: str = "en") -> None:
        if language not in {"en", "de"}:
            raise ValueError("Supported languages are en and de")
        self.endpoint, self.language = endpoint, language

    def transcribe(self, audio: bytes, cancel: Cancellation) -> str:
        cancel.check()
        decode_wav(audio, require_sound=True)
        boundary = uuid.uuid4().hex
        fields = {
            "model": self.endpoint.model,
            "language": self.language,
            "response_format": "json",
        }
        parts = [
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n'
            f"{value}\r\n".encode()
            for key, value in fields.items()
        ]
        parts.append(
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                'filename="speech.wav"\r\nContent-Type: audio/wav\r\n\r\n'
            ).encode()
            + audio
            + f"\r\n--{boundary}--\r\n".encode()
        )
        raw = self.endpoint.post(
            b"".join(parts), f"multipart/form-data; boundary={boundary}", cancel
        )
        try:
            text = json.loads(raw)["text"]
            if not isinstance(text, str) or not text.strip() or len(text) > 4096:
                raise ValueError("Invalid transcription")
            return text
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderError("Invalid transcription response") from exc


class CloudTTS:
    def __init__(
        self, endpoint: Endpoint, voice: str, language: str = "en", rate: float = 1
    ) -> None:
        if not voice or language not in {"en", "de"} or not 0.25 <= rate <= 4:
            raise ValueError("Invalid speech settings")
        self.endpoint, self.voice, self.language, self.rate = endpoint, voice, language, rate

    def synthesize(self, text: str, cancel: Cancellation) -> bytes:
        if not text.strip() or len(text) > 4096:
            raise ValueError("Speech text must contain 1–4096 characters")
        # OpenAI speech has no language field: language follows input text/selected voice.
        payload = json.dumps(
            {
                "model": self.endpoint.model,
                "input": text,
                "voice": self.voice,
                "response_format": "wav",
                "speed": self.rate,
            }
        ).encode()
        audio = self.endpoint.post(payload, "application/json", cancel, MAX_AUDIO_BYTES)
        decode_wav(audio)
        return audio
