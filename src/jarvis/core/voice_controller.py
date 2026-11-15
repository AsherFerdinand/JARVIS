"""One worker per explicit activation; no workers or devices while idle."""

import time
import uuid
from dataclasses import dataclass, field
from threading import Event, Lock, Thread

from jarvis.core.cancellation import Cancellation, Cancelled
from jarvis.core.lifecycle import Assistant
from jarvis.integration.protocol import event
from jarvis.intelligence.conversation import Conversation, PendingTurn
from jarvis.intelligence.errors import ProviderError
from jarvis.speech.audio import AudioError
from jarvis.speech.ports import Capture, Playback, Synthesizer, Transcriber
from jarvis.speech.session import TERMINAL, SessionState, State


@dataclass
class VoiceResult:
    session_id: str
    state: SessionState = field(default_factory=SessionState)
    recognized_text: str | None = None
    response: str | None = None
    error_code: str | None = None
    total_tokens: int | None = None
    timings_ms: dict[str, float] = field(default_factory=dict)


class VoiceController:
    def __init__(
        self,
        assistant: Assistant,
        capture: Capture,
        stt: Transcriber,
        tts: Synthesizer | None,
        playback: Playback | None,
        conversation: Conversation | None = None,
        max_seconds: float = 20,
        share_transcript: bool = False,
        language: str = "en",
    ) -> None:
        if (
            not 0 < max_seconds <= 60
            or (tts is None) != (playback is None)
            or language not in {"en", "de"}
        ):
            raise ValueError("Invalid voice configuration")
        self.assistant, self.capture, self.stt = assistant, capture, stt
        self.tts, self.playback, self.conversation = tts, playback, conversation
        self.max_seconds, self.share_transcript = max_seconds, share_transcript
        self.language = language
        self._lock = Lock()
        self._closed = False
        self._thread: Thread | None = None
        self._cancel = Cancellation()
        self._release = Event()
        self.result: VoiceResult | None = None

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def start(self) -> str:
        with self._lock:
            if self._closed:
                raise RuntimeError("Voice controller closed")
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("A voice session is already active or draining")
            if not self.assistant.running:
                raise RuntimeError("Assistant stopped")
            self._cancel, self._release = Cancellation(), Event()
            self.result = VoiceResult(str(uuid.uuid4()))
            self._thread = Thread(
                target=self._run,
                args=(self.result, self._cancel, self._release),
                daemon=True,
                name="jarvis-voice",
            )
            self._thread.start()
            return self.result.session_id

    def release(self, session_id: str | None = None) -> None:
        with self._lock:
            if session_id is not None and (
                self.result is None or self.result.session_id != session_id
            ):
                return
            release = self._release
        release.set()

    def cancel(self, session_id: str | None = None) -> None:
        with self._lock:
            if session_id is not None and (
                self.result is None or self.result.session_id != session_id
            ):
                return
            cancel, release = self._cancel, self._release
        cancel.cancel()
        release.set()

    def wait(self, timeout: float | None = None) -> VoiceResult:
        with self._lock:
            thread, result = self._thread, self.result
        if thread is None or result is None:
            raise RuntimeError("No voice session")
        thread.join(timeout)
        if thread.is_alive():
            raise TimeoutError("Voice session still draining")
        return result

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self.cancel()
        try:
            self.wait(2)
        except (RuntimeError, TimeoutError):
            pass

    def _run(self, result: VoiceResult, cancel: Cancellation, release: Event) -> None:
        started = time.perf_counter()
        playback_started = False
        pending: PendingTurn | None = None

        def emit(kind: str, *, text: str | None = None, error: str | None = None) -> None:
            self.assistant.events.publish(
                event(
                    kind,
                    result.session_id,
                    session_id=result.session_id,
                    recognized_text=text,
                    error_info=error,
                )
            )

        def move(target: State) -> None:
            result.state.move(target)
            kinds = {
                State.LISTENING: "assistant.listening",
                State.TRANSCRIBING: "assistant.transcribing",
                State.PROCESSING: "assistant.processing",
                State.SPEAKING: "assistant.speaking",
                State.COMPLETED: "voice.session.completed",
                State.FAILED: "voice.session.failed",
                State.CANCELLED: "voice.session.cancelled",
            }
            if target in kinds:
                emit(kinds[target], error=result.error_code)

        try:
            cancel.check()
            move(State.LISTENING)
            phase = time.perf_counter()
            audio = self.capture.record(release, cancel, self.max_seconds)
            result.timings_ms["capture"] = (time.perf_counter() - phase) * 1000
            cancel.check()
            move(State.TRANSCRIBING)
            phase = time.perf_counter()
            text = self.stt.transcribe(audio, cancel)
            del audio
            cancel.check()
            if not isinstance(text, str) or not text.strip() or len(text) > 4096:
                raise AudioError("Invalid or empty transcription")
            result.recognized_text = text
            result.timings_ms["transcription"] = (time.perf_counter() - phase) * 1000
            emit("voice.transcription.completed", text=text if self.share_transcript else None)
            move(State.PROCESSING)
            phase = time.perf_counter()
            intent = self.assistant.router.route(text)
            if intent is not None:
                move(State.EXECUTING)
                result.response = cancel.commit(
                    lambda: self.assistant.handle(
                        text,
                        correlation_id=result.session_id,
                        session_id=result.session_id,
                        emit_status=False,
                    )
                )
            elif self.conversation is not None:
                # Conversations return plain text only. They cannot invoke any action,
                # including an uncertain multi-command transcription.
                pending = self.conversation.prepare(text, cancel)
                reply = pending.reply
                result.response, result.total_tokens = reply.text, reply.total_tokens
            else:
                raise ValueError("Unknown command and no conversation provider")
            cancel.check()
            result.timings_ms["processing"] = (time.perf_counter() - phase) * 1000
            if self.tts is not None and self.playback is not None:
                move(State.SPEAKING)
                phase = time.perf_counter()
                speech_text = result.response
                if self.language == "de" and intent is not None:
                    confirmations = {
                        "open_website": "Webseite geöffnet.",
                        "open_application": "Anwendung ist bereit.",
                        "assistant_status": "JARVIS ist bereit.",
                        "exit": "JARVIS wurde beendet.",
                        "system_info": f"Systeminformationen: {result.response}",
                        "application_status": f"Anwendungsstatus: {result.response}",
                    }
                    speech_text = confirmations[intent.action]
                spoken = self.tts.synthesize(speech_text, cancel)
                cancel.check()
                playback_started = True
                self.playback.play(spoken, cancel)
                del spoken
                cancel.check()
                result.timings_ms["speech"] = (time.perf_counter() - phase) * 1000
                emit("voice.playback.completed")

            def complete() -> None:
                if pending is not None and self.conversation is not None:
                    self.conversation.commit_turn(pending, cancel)
                move(State.COMPLETED)

            cancel.commit(complete)
        except Cancelled:
            result.response = None
            if playback_started:
                emit("voice.playback.cancelled")
            move(State.CANCELLED)
        except Exception as exc:
            if cancel.event.is_set():
                result.response = None
                if playback_started:
                    emit("voice.playback.cancelled")
                move(State.CANCELLED)
            else:
                result.error_code = (
                    exc.code if isinstance(exc, AudioError | ProviderError) else "voice_failure"
                )
                move(State.FAILED)
        finally:
            result.timings_ms["total"] = (time.perf_counter() - started) * 1000
            if result.state.current not in TERMINAL:
                result.error_code = "voice_failure"
                move(State.FAILED)
            emit("assistant.idle")


class PushToTalkAdapter:
    """Press/release boundary for an in-app trigger or future consented global shortcut."""

    def __init__(self, controller: VoiceController) -> None:
        self.controller = controller
        self.session_id: str | None = None

    def press(self) -> str:
        self.session_id = self.controller.start()
        return self.session_id

    def release(self) -> None:
        if self.session_id is not None:
            self.controller.release(self.session_id)

    def cancel(self) -> None:
        if self.session_id is not None:
            self.controller.cancel(self.session_id)
