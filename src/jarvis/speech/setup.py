"""Voice configuration is read only when voice is explicitly requested."""

import os
from pathlib import Path

from jarvis.core.lifecycle import Assistant
from jarvis.core.voice_controller import VoiceController
from jarvis.intelligence.conversation import Conversation, MockConversation
from jarvis.intelligence.preflight import capabilities, require_valid
from jarvis.speech.audio_capture import (
    DevicePlayback,
    FileCapture,
    MicrophoneCapture,
    MockCapture,
    MockPlayback,
)
from jarvis.speech.cloud import CloudSTT, CloudTTS, Endpoint
from jarvis.speech.mocks import MockSTT, MockTTS
from jarvis.speech.ports import Capture, Playback, Synthesizer


def endpoint_from_environment(prefix: str) -> Endpoint:
    require_valid(prefix.removeprefix("JARVIS_"), os.environ)
    url, model, key = (os.getenv(f"{prefix}_{field}", "") for field in ("URL", "MODEL", "KEY"))
    if not all((url, model, key)):
        raise ValueError(f"Configure {prefix}_URL, {prefix}_MODEL and {prefix}_KEY")
    return Endpoint(
        url,
        key,
        model,
        float(os.getenv(f"{prefix}_TIMEOUT", "15")),
        float(os.getenv(f"{prefix}_CONNECT_TIMEOUT", "10")),
        float(os.getenv(f"{prefix}_DEADLINE", "30")),
    )


def make_voice(
    assistant: Assistant,
    *,
    mock_text: str | None = None,
    audio_file: Path | None = None,
    speak: bool = True,
    mock_audio: bool = False,
) -> VoiceController:
    if mock_text is not None:
        return VoiceController(
            assistant,
            MockCapture(),
            MockSTT(mock_text),
            MockTTS() if speak else None,
            MockPlayback() if speak else None,
            Conversation(MockConversation()),
        )
    language = os.getenv("JARVIS_VOICE_LANGUAGE", "en")
    stt = CloudSTT(
        endpoint_from_environment("JARVIS_STT"),
        language,
        response_format=os.getenv("JARVIS_STT_RESPONSE_FORMAT", "json"),
        language_hint=capabilities("STT", os.environ).language_hint,
    )
    tts: Synthesizer | None = None
    playback: Playback | None = None
    if speak:
        voice = os.getenv("JARVIS_TTS_VOICE", "")
        tts = CloudTTS(
            endpoint_from_environment("JARVIS_TTS"),
            voice,
            language,
            float(os.getenv("JARVIS_TTS_RATE", "1")),
            speaking_rate=capabilities("TTS", os.environ).speaking_rate,
        )
        playback = (
            MockPlayback() if mock_audio else DevicePlayback(os.getenv("JARVIS_OUTPUT_DEVICE"))
        )
    capture: Capture = (
        FileCapture(audio_file)
        if audio_file
        else MockCapture()
        if mock_audio
        else MicrophoneCapture(os.getenv("JARVIS_INPUT_DEVICE"))
    )
    return VoiceController(
        assistant,
        capture,
        stt,
        tts,
        playback,
        assistant.conversation,
        float(os.getenv("JARVIS_RECORD_SECONDS", "20")),
        os.getenv("JARVIS_SHARE_TRANSCRIPT", "0") == "1",
        language=language,
    )
