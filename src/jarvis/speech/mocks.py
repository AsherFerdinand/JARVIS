from jarvis.core.cancellation import Cancellation
from jarvis.speech.audio import decode_wav, synthetic_wav


class MockSTT:
    def __init__(self, text: str) -> None:
        self.text = text

    def transcribe(self, audio: bytes, cancel: Cancellation) -> str:
        cancel.check()
        decode_wav(audio, require_sound=True)
        return self.text


class MockTTS:
    def synthesize(self, text: str, cancel: Cancellation) -> bytes:
        cancel.check()
        return synthetic_wav()
