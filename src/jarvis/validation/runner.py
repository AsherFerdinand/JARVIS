"""Explicit independent checks. No consent, device or provider is inferred from startup."""

import ipaddress
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from urllib.parse import urlsplit

from jarvis import __version__
from jarvis.actions.windows import MockExecutor, WindowsExecutor
from jarvis.config import Config
from jarvis.core.cancellation import Cancellation, Cancelled
from jarvis.core.lifecycle import Assistant
from jarvis.core.voice_controller import VoiceController
from jarvis.intelligence.conversation import CloudConversation, Conversation
from jarvis.intelligence.errors import ProviderError
from jarvis.intelligence.preflight import capabilities, preflight
from jarvis.speech.audio import AudioError
from jarvis.speech.audio_capture import DevicePlayback, FileCapture, MicrophoneCapture
from jarvis.speech.audio_devices import audio_backend, inventory
from jarvis.speech.cloud import CloudSTT, CloudTTS
from jarvis.speech.ports import Capture, Playback, Synthesizer, Transcriber
from jarvis.speech.setup import endpoint_from_environment, make_voice
from jarvis.validation.signals import inspect_signal, tone

STAGES = (
    "offline",
    "backend",
    "devices",
    "microphone",
    "speaker",
    "stt",
    "chat",
    "tts",
    "interaction",
)


@dataclass(frozen=True)
class Consent:
    microphone: bool = False
    playback: bool = False
    network: bool = False
    actions: bool = False


class Blocked(Exception):
    pass


class TimedSTT:
    def __init__(self, delegate: Transcriber, timings: dict[str, float]) -> None:
        self.delegate, self.timings = delegate, timings

    def transcribe(self, audio: bytes, cancel: Cancellation) -> str:
        started = time.perf_counter()
        try:
            return self.delegate.transcribe(audio, cancel)
        finally:
            self.timings["stt_request_wall_ms"] = (time.perf_counter() - started) * 1000


class TimedTTS:
    def __init__(self, delegate: Synthesizer, timings: dict[str, float]) -> None:
        self.delegate, self.timings = delegate, timings

    def synthesize(self, text: str, cancel: Cancellation) -> bytes:
        started = time.perf_counter()
        try:
            return self.delegate.synthesize(text, cancel)
        finally:
            self.timings["tts_request_wall_ms"] = (time.perf_counter() - started) * 1000


class Validator:
    def __init__(
        self,
        settings: Mapping[str, str] | None = None,
        *,
        capture: Capture | None = None,
        playback: Playback | None = None,
        consent: Consent | None = None,
        seconds: float = 2,
        volume: float = 0.03,
        show_text: bool = False,
        cancel: Cancellation | None = None,
    ) -> None:
        self.settings = os.environ if settings is None else settings
        self.capture, self.playback = capture, playback
        self.consent, self.seconds, self.volume, self.show_text = (
            consent or Consent(),
            seconds,
            volume,
            show_text,
        )
        self.cancel = cancel or Cancellation()
        self.timings: dict[str, float] = {}
        self.details: dict[str, object] = {}
        self.effects = {
            name: "not_requested" for name in ("microphone", "playback", "network", "actions")
        }

    def _require(self, name: str) -> None:
        if not getattr(self.consent, name):
            raise Blocked(f"consent_{name}_required")

    def _duration(self) -> None:
        if not 0 < self.seconds <= 5:
            raise ValueError("Short validation samples require >0 and <=5 seconds")

    def _capture(self) -> bytes:
        self._require("microphone")
        self._duration()
        self.cancel.check()
        self.effects["microphone"] = "api_attempted"
        device = self.capture or MicrophoneCapture(
            self.settings.get("JARVIS_INPUT_DEVICE"), timings=self.timings, require_signal=False
        )
        started = time.perf_counter()
        try:
            audio = device.record(Event(), self.cancel, self.seconds)
        finally:
            self.timings["capture_local_wall_ms"] = (time.perf_counter() - started) * 1000
        self.cancel.check()
        self.effects["microphone"] = "capture_completed"
        return audio

    def _play(self, audio: bytes) -> None:
        self._require("playback")
        self.cancel.check()
        self.effects["playback"] = "api_attempted"
        output = self.playback or DevicePlayback(
            self.settings.get("JARVIS_OUTPUT_DEVICE"), timings=self.timings
        )
        started = time.perf_counter()
        try:
            output.play(audio, self.cancel)
        finally:
            self.timings["playback_local_wall_ms"] = (time.perf_counter() - started) * 1000
        self.cancel.check()
        self.effects["playback"] = "api_completed"
        self.details["audible_confirmed"] = False

    def _stt(self) -> CloudSTT:
        return CloudSTT(
            endpoint_from_environment("JARVIS_STT", self.settings),
            self.settings.get("JARVIS_VOICE_LANGUAGE", "en"),
            allow_empty=True,
            response_format=self.settings.get("JARVIS_STT_RESPONSE_FORMAT", "json"),
            language_hint=capabilities("STT", self.settings).language_hint,
        )

    def _tts(self) -> CloudTTS:
        return CloudTTS(
            endpoint_from_environment("JARVIS_TTS", self.settings),
            self.settings.get("JARVIS_TTS_VOICE", ""),
            self.settings.get("JARVIS_VOICE_LANGUAGE", "en"),
            float(self.settings.get("JARVIS_TTS_RATE", "1")),
            speaking_rate=capabilities("TTS", self.settings).speaking_rate,
        )

    def _chat(self) -> CloudConversation:
        return CloudConversation(
            endpoint_from_environment("JARVIS_AI", self.settings),
            system_role=self.settings.get("JARVIS_AI_SYSTEM_ROLE", "system"),
        )

    def _network_scope(self, role: str) -> None:
        host = urlsplit(self.settings.get(f"JARVIS_{role}_URL", "")).hostname or ""
        try:
            local = host == "localhost" or ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = host == "localhost"
        self.effects["network"] = "configured_http_attempted"
        self.details["endpoint_scope"] = "loopback" if local else "external_or_proxy"
        self.details["speech_or_language_quality_verified"] = False

    def _interaction(self, speak: bool, release: Callable[[VoiceController], None] | None) -> None:
        self._require("microphone")
        self._require("network")
        if speak:
            self._require("playback")
        self._duration()
        conversation = None
        if any(self.settings.get(f"JARVIS_AI_{field}") for field in ("URL", "MODEL", "KEY")):
            conversation = Conversation(
                self._chat(), language=self.settings.get("JARVIS_VOICE_LANGUAGE", "en")
            )
        executor = WindowsExecutor() if self.consent.actions else MockExecutor()
        assistant = Assistant(Config(), executor, conversation=conversation)
        voice: VoiceController | None = None
        try:
            voice = make_voice(assistant, speak=speak, environment=self.settings)
            voice.max_seconds = self.seconds
            voice.capture = self.capture or MicrophoneCapture(
                self.settings.get("JARVIS_INPUT_DEVICE"), timings=self.timings
            )
            if speak:
                voice.playback = self.playback or DevicePlayback(
                    self.settings.get("JARVIS_OUTPUT_DEVICE"), timings=self.timings
                )
            voice.stt = TimedSTT(voice.stt, self.timings)
            if voice.tts is not None:
                voice.tts = TimedTTS(voice.tts, self.timings)
            self._network_scope("STT")
            self.effects["microphone"] = "api_attempted"
            self.effects["actions"] = (
                "approved_registry_allowed" if self.consent.actions else "mock_execution"
            )
            if speak:
                self.effects["playback"] = "api_attempted"
            voice.start()
            if release is not None:
                release(voice)
            # Bounded join slices allow the caller's cancellation token to reach the controller.
            while True:
                if self.cancel.event.is_set():
                    voice.cancel()
                    raise Cancelled()
                try:
                    result = voice.wait(0.05)
                    break
                except TimeoutError:
                    continue
            self.cancel.check()
            if result.state.current == "cancelled":
                raise Cancelled()
            if result.state.current != "completed":
                raise ProviderError(
                    "Interaction did not complete", code=result.error_code or "validation_failed"
                )
            self.details.update(
                {
                    "recognized_characters": len(result.recognized_text or ""),
                    "reply_characters": len(result.response or ""),
                    "total_tokens": result.total_tokens,
                    "audible_confirmed": False,
                }
            )
            for name, value in result.timings_ms.items():
                self.timings[f"interaction_{name}_wall_ms"] = value
            if self.show_text:
                self.details.update(
                    {"recognized_text": result.recognized_text, "reply_text": result.response}
                )
        finally:
            if voice is not None:
                voice.close()
            assistant.close()

    def run(
        self,
        stage: str,
        *,
        source: str = "synthetic",
        file: Path | None = None,
        speak: bool = True,
        release: Callable[[VoiceController], None] | None = None,
    ) -> dict[str, object]:
        self.timings, self.details = {}, {}
        self.effects = dict.fromkeys(self.effects, "not_requested")
        started = time.perf_counter()
        outcome = "passed"
        error: dict[str, object] | None = None
        try:
            self.cancel.check()
            if stage == "offline":
                report = preflight(self.settings)
                self.details["configuration"] = report
                if not report["valid_configured_providers"]:
                    outcome, error = "failed", {"code": "configuration_invalid"}
            elif stage == "backend":
                begin = time.perf_counter()
                audio_backend()
                self.timings["audio_backend_init_local_ms"] = (time.perf_counter() - begin) * 1000
                self.details["backend_loaded"] = True
            elif stage == "devices":
                rows = inventory(audio_backend())
                self.details["devices"] = [
                    {
                        "index": row.index,
                        "input_channels": row.inputs,
                        "output_channels": row.outputs,
                        "native_rate": row.rate,
                    }
                    for row in rows
                ]
                self.details["streams_opened"] = 0
            elif stage == "microphone":
                self.details.update(inspect_signal(self._capture()))
                if not self.details["signal_detected"]:
                    outcome, error = "failed", {"code": "insufficient_signal"}
            elif stage == "speaker":
                self._require("playback")
                self._duration()
                self._play(tone(min(self.seconds, 2), self.volume))
                self.details["signal_source"] = "bounded_synthetic_tone"
            elif stage == "stt":
                self._require("network")
                client = self._stt()
                if source == "microphone":
                    audio = self._capture()
                elif source == "file" and file is not None:
                    self._duration()
                    audio = FileCapture(file).record(Event(), self.cancel, self.seconds)
                elif source == "synthetic":
                    audio = tone(0.3, self.volume)
                else:
                    raise ValueError("Invalid STT validation source")
                self._network_scope("STT")
                text = TimedSTT(client, self.timings).transcribe(audio, self.cancel)
                self.details.update(
                    {
                        "http_contract_passed": True,
                        "audio_source": source,
                        "recognized_characters": len(text),
                        "transcription_nonempty": bool(text.strip()),
                    }
                )
                if self.show_text:
                    self.details["recognized_text"] = text
            elif stage == "chat":
                self._require("network")
                client_chat = self._chat()
                self._network_scope("AI")
                language = self.settings.get("JARVIS_VOICE_LANGUAGE", "en")
                prompt = (
                    "Was ist Rekuperation?"
                    if language == "de"
                    else "Explain regenerative braking briefly."
                )
                begin = time.perf_counter()
                reply = client_chat.respond(
                    [
                        {"role": "system", "content": f"Reply briefly in {language}."},
                        {"role": "user", "content": prompt},
                    ],
                    self.cancel,
                )
                self.timings["ai_request_wall_ms"] = (time.perf_counter() - begin) * 1000
                self.details.update(
                    {
                        "http_contract_passed": True,
                        "reply_characters": len(reply.text),
                        "language_requested": language,
                        "total_tokens": reply.total_tokens,
                    }
                )
                if self.show_text:
                    self.details["reply_text"] = reply.text
            elif stage == "tts":
                self._require("network")
                client_tts = self._tts()
                self._network_scope("TTS")
                text = (
                    "JARVIS Sprachtest."
                    if self.settings.get("JARVIS_VOICE_LANGUAGE", "en") == "de"
                    else "JARVIS speech test."
                )
                audio = TimedTTS(client_tts, self.timings).synthesize(text, self.cancel)
                self.details.update(inspect_signal(audio))
                self.details["http_contract_passed"] = True
                if self.consent.playback:
                    self._play(audio)
            elif stage == "interaction":
                self._interaction(speak, release)
            else:
                raise ValueError("Unknown validation stage")
            self.cancel.check()
        except Blocked as exc:
            outcome, error = "blocked", {"code": str(exc)}
        except (Cancelled, KeyboardInterrupt):
            self.cancel.cancel()
            outcome, error = "cancelled", {"code": "cancelled"}
        except ProviderError as exc:
            outcome, error = "failed", exc.to_dict()
        except AudioError as exc:
            outcome, error = "failed", {"code": exc.code}
        except (ValueError, OSError, RuntimeError):
            outcome, error = "failed", {"code": "validation_configuration_or_device_error"}
        self.timings["total_wall_ms"] = (time.perf_counter() - started) * 1000
        return {
            "version": __version__,
            "stage": stage,
            "outcome": outcome,
            "error": error,
            "audio_mode": "injected_simulation"
            if self.capture is not None or self.playback is not None
            else "native_api",
            "effects": self.effects,
            "details": self.details,
            "timings_ms": self.timings,
            "raw_audio_saved": False,
            "text_included": self.show_text,
            "representative_hardware_verified": False,
            "audible_confirmed": False,
        }
