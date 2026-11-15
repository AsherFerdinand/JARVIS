import json
import threading
import time

import pytest
from test_voice import make_controller

from jarvis.core.cancellation import Cancellation, Cancelled
from jarvis.core.voice_controller import PushToTalkAdapter
from jarvis.diagnostics.health import health
from jarvis.intelligence.conversation import Conversation, MockConversation
from jarvis.speech.audio import synthetic_wav
from jarvis.speech.session import State


def test_cancel_before_action_commit():
    entered, release = threading.Event(), threading.Event()
    controller = make_controller()
    route = controller.assistant.router.route

    def held(text):
        entered.set()
        assert release.wait(3)
        return route(text)

    controller.assistant.router.route = held
    controller.start()
    assert entered.wait(3)
    controller.cancel()
    release.set()
    result = controller.wait(3)
    assert result.state.current == State.CANCELLED
    assert not controller.assistant.executor.calls


def test_cancelled_speech_does_not_commit_conversation():
    entered = threading.Event()

    class HeldPlayback:
        def play(self, audio, cancel):
            entered.set()
            assert cancel.event.wait(3)
            cancel.check()

    conversation = Conversation(MockConversation())
    controller = make_controller("explain", conversation=conversation, playback=HeldPlayback())
    controller.start()
    assert entered.wait(3)
    controller.cancel()
    result = controller.wait(3)
    assert result.state.current == State.CANCELLED
    assert result.response is None
    assert not conversation.history


def test_close_is_bounded_even_when_custom_executor_hangs():
    entered, release = threading.Event(), threading.Event()
    controller = make_controller()

    def blocked(url):
        entered.set()
        assert release.wait(5)
        return "opened"

    controller.assistant.executor.open_website = blocked
    controller.start()
    assert entered.wait(3)
    started = time.monotonic()
    try:
        controller.close()
        assert time.monotonic() - started < 2.5
        with pytest.raises(RuntimeError, match="closed"):
            controller.start()
    finally:
        release.set()
        controller.wait(3)


def test_cancel_never_waits_for_committed_operation():
    token = Cancellation()
    entered = threading.Event()
    release = threading.Event()

    def commit():
        token.commit(lambda: (entered.set(), release.wait(3)))

    thread = threading.Thread(target=commit)
    thread.start()
    assert entered.wait(3)
    started = time.monotonic()
    token.cancel()
    assert time.monotonic() - started < 0.1
    release.set()
    thread.join(3)
    with pytest.raises(Cancelled):
        token.commit(lambda: None)


def test_stale_activation_adapter_cannot_cancel_new_session():
    controller = make_controller()
    old = PushToTalkAdapter(controller)
    old.press()
    controller.wait(3)
    entered = threading.Event()

    class Capture:
        def record(self, release, cancel, seconds):
            entered.set()
            assert release.wait(3)
            cancel.check()
            return synthetic_wav()

    controller.capture = Capture()
    new = PushToTalkAdapter(controller)
    new.press()
    assert entered.wait(3)
    old.cancel()
    old.release()
    assert not controller._cancel.event.is_set()
    assert not controller._release.is_set()
    new.release()
    assert controller.wait(3).state.current == State.COMPLETED


def test_repeated_activations_stay_bounded():
    before = {t.ident for t in threading.enumerate()}
    controller = make_controller()
    for _ in range(100):
        controller.start()
        assert controller.wait(3).state.current == State.COMPLETED
    assert len(controller.assistant.events.snapshot()) == 128
    assert {t.ident for t in threading.enumerate()} == before
    controller.close()


def test_health_never_discloses_configuration_values():
    values = {
        "JARVIS_AI_KEY": "private-key",
        "JARVIS_AI_URL": "https://private-host",
        "JARVIS_INPUT_DEVICE": "personal headset",
    }
    report = health(environment=values)
    serialized = json.dumps(report)
    assert all(value not in serialized for value in values.values())
    assert report["providers"]["JARVIS_AI"]["partial"]
    assert report["selected_devices"]["INPUT"] == "explicit"
    assert report["audio_backend"] in {"not_probed", "not_installed"}


def test_event_server_shutdown_interrupts_incomplete_headers():
    import socket

    from jarvis.integration.server import EventServer

    controller = make_controller()
    server = EventServer(controller.assistant.events, "a" * 48)
    server.start()
    with socket.create_connection(("127.0.0.1", server.port), timeout=2) as client:
        client.sendall(b"GET /v1/events HTTP/1.1\r\nX-Hold: ")
        started = time.monotonic()
        server.close()
        assert time.monotonic() - started < 1.5
    assert not server._thread.is_alive()
