import json

import pytest

from jarvis.actions.windows import MockExecutor
from jarvis.config import Config
from jarvis.core.lifecycle import Assistant
from jarvis.integration.protocol import EVENT_TYPES, Event, event


@pytest.mark.parametrize("kind", sorted(EVENT_TYPES))
def test_v1_event_shape(kind):
    value = json.loads(json.dumps(event(kind, "correlation").to_dict()))
    assert set(value) == {
        "version",
        "id",
        "timestamp",
        "correlation_id",
        "event",
        "application",
        "display_text",
        "icon",
        "progress",
    }
    assert value["version"] == 1
    assert value["timestamp"] > 0
    assert value["id"]
    assert value["event"] == kind


def test_command_order_and_correlation():
    assistant = Assistant(Config(), MockExecutor())
    assistant.handle("open youtube")
    events = assistant.events.snapshot()[1:]
    assert [e.event for e in events] == [
        "assistant.processing",
        "command.executing",
        "command.completed",
        "assistant.idle",
    ]
    assert len({e.correlation_id for e in events}) == 1
    assert len({e.id for e in events}) == 4


def test_invalid_protocol():
    with pytest.raises(ValueError):
        Event(2, "id", 1, "c", "assistant.idle")
    with pytest.raises(ValueError):
        Event(1, "id", 1, "c", "assistant.idle", progress=1.1)
