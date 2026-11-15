import io
import json
from email import policy
from email.parser import BytesParser
from urllib.error import HTTPError, URLError

import pytest

from jarvis.core.cancellation import Cancellation, Cancelled
from jarvis.intelligence.conversation import CloudConversation
from jarvis.intelligence.provider import ProviderError
from jarvis.intelligence.transport import exchange, unwrap
from jarvis.speech.audio import AudioError, decode_wav, encode_wav, synthetic_wav
from jarvis.speech.cloud import CloudSTT, CloudTTS, Endpoint


class Transport:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def open(self, request, timeout):
        assert timeout == 3
        self.requests.append(request)
        return io.BytesIO(self.response)


@pytest.fixture
def transport(monkeypatch):
    fake = Transport(b"{}")
    monkeypatch.setattr(
        "jarvis.intelligence.transport.ProcessTransport.request",
        lambda self, call, cancel, total: unwrap(exchange(call, fake)),
    )
    return fake


def endpoint():
    return Endpoint(
        "https://api.example/v1/audio/transcriptions", "test-key", "configured-model", 3
    )


@pytest.mark.parametrize("language,text", [("en", "Open YouTube."), ("de", "Öffne YouTube.")])
def test_stt_multipart_documented_format(transport, language, text):
    transport.response = json.dumps({"text": text}).encode()
    audio = synthetic_wav()
    assert CloudSTT(endpoint(), language).transcribe(audio, Cancellation()) == text
    request = transport.requests[0]
    message = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {request.get_header('Content-type')}\r\n\r\n".encode() + request.data
    )
    parts = {
        part.get_param("name", header="content-disposition"): part for part in message.iter_parts()
    }
    assert parts["file"].get_payload(decode=True) == audio
    assert parts["file"].get_filename() == "speech.wav"
    assert parts["language"].get_payload() == language
    assert parts["model"].get_payload() == "configured-model"
    assert parts["response_format"].get_payload() == "json"
    assert request.get_header("Authorization") == "Bearer test-key"


@pytest.mark.parametrize(
    "response",
    [
        b"{}",
        b"[]",
        b"bad",
        b'{"text":""}',
        b'{"text":1}',
        json.dumps({"text": "a" * 4097}).encode(),
    ],
    ids=["missing", "array", "json", "empty", "type", "oversize"],
)
def test_stt_invalid_response(transport, response):
    transport.response = response
    with pytest.raises(ProviderError):
        CloudSTT(endpoint()).transcribe(synthetic_wav(), Cancellation())


@pytest.mark.parametrize("audio", [b"bad", encode_wav(b"\x00\x00" * 100), synthetic_wav()[:-10]])
def test_bad_audio_never_uploaded(transport, audio):
    with pytest.raises(AudioError):
        CloudSTT(endpoint()).transcribe(audio, Cancellation())
    assert not transport.requests


def test_tts_documented_json_wav(transport):
    transport.response = synthetic_wav()
    assert CloudTTS(endpoint(), "configured-voice", "de", 1.25).synthesize("Hallo!", Cancellation())
    payload = json.loads(transport.requests[0].data)
    assert payload == {
        "model": "configured-model",
        "voice": "configured-voice",
        "input": "Hallo!",
        "speed": 1.25,
        "response_format": "wav",
    }


@pytest.mark.parametrize(
    "failure",
    [
        TimeoutError(),
        URLError("offline"),
        HTTPError("https://api.example", 401, "Unauthorized", {}, None),
    ],
)
def test_network_failure(monkeypatch, failure):
    class Broken:
        def open(self, *args, **kwargs):
            raise failure

    monkeypatch.setattr(
        "jarvis.intelligence.transport.ProcessTransport.request",
        lambda self, call, cancel, total: unwrap(exchange(call, Broken())),
    )
    with pytest.raises(ProviderError):
        CloudSTT(endpoint()).transcribe(synthetic_wav(), Cancellation())


def test_response_bounds_and_cancellation(transport):
    transport.response = b"x" * 65537
    with pytest.raises(ProviderError):
        endpoint().post(b"{}", "application/json", Cancellation())
    cancel = Cancellation()
    cancel.cancel()
    count = len(transport.requests)
    with pytest.raises(Cancelled):
        endpoint().post(b"{}", "application/json", cancel)
    assert len(transport.requests) == count


@pytest.mark.parametrize(
    "url,key,model,timeout",
    [
        ("http://api.example", "key", "m", 3),
        ("https://u:p@api.example", "key", "m", 3),
        ("https://api.example", "", "m", 3),
        ("https://api.example", "key", "", 3),
        ("https://api.example", "key", "m", 0),
    ],
)
def test_endpoint_configuration(url, key, model, timeout):
    with pytest.raises(ValueError):
        Endpoint(url, key, model, timeout)


def test_conversation_wire_and_usage(transport):
    transport.response = json.dumps(
        {"choices": [{"message": {"content": "An explanation."}}], "usage": {"total_tokens": 18}}
    ).encode()
    reply = CloudConversation(endpoint()).respond(
        [{"role": "user", "content": "Explain"}], Cancellation()
    )
    assert reply.text == "An explanation."
    assert reply.total_tokens == 18
    assert "tools" not in json.loads(transport.requests[0].data)


@pytest.mark.parametrize(
    "response", [b"{}", b"bad", b'{"choices": []}', b'{"choices":[{"message":{"content":null}}]}']
)
def test_conversation_bad_response(transport, response):
    transport.response = response
    with pytest.raises(ProviderError):
        CloudConversation(endpoint()).respond([], Cancellation())


def test_streaming_wav_sentinel_is_bounded():
    audio = bytearray(synthetic_wav())
    audio[4:8] = (0xFFFFFFFF).to_bytes(4, "little")
    audio[40:44] = (0xFFFFFFFF).to_bytes(4, "little")
    assert decode_wav(bytes(audio)).data == decode_wav(synthetic_wav()).data
