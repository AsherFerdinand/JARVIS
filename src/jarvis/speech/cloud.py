"""Documented OpenAI audio REST formats; endpoints/models supplied explicitly."""

import json
import uuid

from jarvis.core.cancellation import Cancellation
from jarvis.intelligence.errors import ProviderError
from jarvis.intelligence.transport import Endpoint as Endpoint
from jarvis.speech.audio import MAX_AUDIO_BYTES, AudioError, decode_wav


class CloudSTT:
    def __init__(
        self,
        endpoint: Endpoint,
        language: str = "en",
        *,
        response_format: str = "json",
        language_hint: bool = True,
        allow_empty: bool = False,
    ) -> None:
        if language not in {"en", "de"}:
            raise ValueError("Supported languages are en and de")
        if response_format not in {"json", "text"}:
            raise ValueError("Unsupported transcription format")
        self.response_format, self.language_hint = response_format, language_hint
        self.allow_empty = allow_empty
        self.endpoint, self.language = endpoint, language

    def transcribe(self, audio: bytes, cancel: Cancellation) -> str:
        cancel.check()
        decode_wav(audio, require_sound=True)
        boundary = uuid.uuid4().hex
        fields = {
            "model": self.endpoint.model,
            "response_format": self.response_format,
        }
        if self.language_hint:
            fields["language"] = self.language
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
            text = (
                raw.decode("utf-8") if self.response_format == "text" else json.loads(raw)["text"]
            )
            if (
                not isinstance(text, str)
                or (not text.strip() and not self.allow_empty)
                or len(text) > 4096
            ):
                raise ValueError("Invalid transcription")
            return text
        except (ValueError, KeyError, TypeError, RecursionError) as exc:
            raise ProviderError("Invalid transcription response") from exc


class CloudTTS:
    def __init__(
        self,
        endpoint: Endpoint,
        voice: str,
        language: str = "en",
        rate: float = 1,
        *,
        speaking_rate: bool = True,
    ) -> None:
        if not voice or language not in {"en", "de"} or not 0.25 <= rate <= 4:
            raise ValueError("Invalid speech settings")
        if not speaking_rate and rate != 1:
            raise ValueError("Speaking rate is not supported by this profile")
        self.speaking_rate = speaking_rate
        self.endpoint, self.voice, self.language, self.rate = endpoint, voice, language, rate

    def synthesize(self, text: str, cancel: Cancellation) -> bytes:
        if not text.strip() or len(text) > 4096:
            raise ValueError("Speech text must contain 1–4096 characters")
        # OpenAI speech has no language field: language follows input text/selected voice.
        fields: dict[str, str | float] = {
            "model": self.endpoint.model,
            "input": text,
            "voice": self.voice,
            "response_format": "wav",
        }
        if self.speaking_rate:
            fields["speed"] = self.rate
        payload = json.dumps(fields).encode()
        audio = self.endpoint.post(payload, "application/json", cancel, MAX_AUDIO_BYTES)
        try:
            decode_wav(audio)
        except AudioError:
            raise ProviderError(
                "Invalid synthesized audio", code="invalid_audio_response"
            ) from None
        return audio
