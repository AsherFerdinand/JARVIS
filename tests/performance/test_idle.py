import threading

from jarvis.actions.windows import MockExecutor
from jarvis.config import Config
from jarvis.core.lifecycle import Assistant


def test_default_core_creates_no_background_workers():
    before = {t.ident for t in threading.enumerate()}
    assistant = Assistant(Config(), MockExecutor())
    for _ in range(200):
        assistant.handle("status")
    assert {t.ident for t in threading.enumerate()} == before
    assert len(assistant.events.snapshot()) == 128
    assistant.close()
