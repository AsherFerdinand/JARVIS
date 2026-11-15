"""Voice configuration is read only when voice is explicitly requested."""

import os
from pathlib import Path

from jarvis.core.lifecycle import Assistant
from jarvis.core.voice_controller import VoiceController
from jarvis.intelligence.conversation import Conversation, MockConversation
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
    url, model, key = (os.getenv(f"{prefix}_{field}", "") for field in ("URL", "MODEL", "KEY"))
    if not all((url, model, key)):
        raise ValueError(f"Configure {prefix}_URL, {prefix}_MODEL and {prefix}_KEY")
    return Endpoint(url, key, model, float(os.getenv(f"{prefix}_TIMEOUT", "15")))


def make_voice(
    assistant: Assistant,
    *,
    mock_text: str | None = None,
    audio_file: Path | None = None,
    speak: bool = True,
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
    stt = CloudSTT(endpoint_from_environment("JARVIS_STT"), language)
    tts: Synthesizer | None = None
    playback: Playback | None = None
    if speak:
        voice = os.getenv("JARVIS_TTS_VOICE", "")
        tts = CloudTTS(
            endpoint_from_environment("JARVIS_TTS"),
            voice,
            language,
            float(os.getenv("JARVIS_TTS_RATE", "1")),
        )
        playback = DevicePlayback(os.getenv("JARVIS_OUTPUT_DEVICE"))
    capture: Capture = (
        FileCapture(audio_file)
        if audio_file
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
    )
