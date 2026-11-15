import pytest

from jarvis.actions.registry import validate
from jarvis.actions.windows import MockExecutor
from jarvis.config import Config
from jarvis.core.event_bus import EventBus
from jarvis.core.lifecycle import Assistant
from jarvis.integration.protocol import event
from jarvis.intelligence.intent import Intent
from jarvis.intelligence.provider import MockProvider, ProviderResult


@pytest.mark.parametrize(
    "text,action,target",
    [
        (" OPEN   YouTube ", "open_website", "youtube"),
        ("open notepad", "open_application", "notepad"),
        ("status notepad", "application_status", "notepad"),
        ("system info", "system_info", None),
        ("status", "assistant_status", None),
        ("exit", "exit", None),
    ],
)
def test_routes(text, action, target):
    assistant = Assistant(Config(), MockExecutor())
    assert assistant.router.route(text) == Intent(action, target)


@pytest.mark.parametrize(
    "intent",
    [
        Intent("shell", "calc.exe"),
        Intent("open_website", "https://evil.example"),
        Intent("open_application", "cmd.exe"),
        Intent("assistant_status", "unexpected"),
        Intent("delete_files"),
    ],
)
def test_registry_denies(intent):
    with pytest.raises(ValueError):
        validate(intent, Config())


def test_lifecycle_actions_and_cleanup():
    executor = MockExecutor()
    assistant = Assistant(Config(), executor)
    assert "opened" in assistant.handle("open youtube")
    assert "opened" in assistant.handle("open notepad")
    assert "notepad" in assistant.handle("status notepad")
    assert assistant.handle("system info")
    assert assistant.handle("status") == "JARVIS ready"
    assert executor.calls == [
        ("website", "https://www.youtube.com"),
        ("application", "notepad.exe"),
    ]
    assert assistant.handle("exit") == "JARVIS stopped"
    with pytest.raises(RuntimeError):
        assistant.handle("status")


def test_unknown_does_not_execute_and_emits_failure():
    executor = MockExecutor()
    assistant = Assistant(Config(), executor)
    with pytest.raises(ValueError):
        assistant.handle("run arbitrary powershell")
    assert executor.calls == []
    assert [e.event for e in assistant.events.snapshot()][-2:] == [
        "command.failed",
        "assistant.idle",
    ]


def test_provider_fallback_and_deterministic_bypass():
    class CountingProvider(MockProvider):
        calls = 0

        def interpret(self, text):
            self.calls += 1
            return super().interpret(text)

    provider = CountingProvider()
    assistant = Assistant(Config(), MockExecutor(), provider)
    assistant.handle("open youtube")
    assert provider.calls == 0
    assert assistant.handle("hello") == "JARVIS ready"
    assert provider.calls == 1
    assert assistant.total_tokens == 0


def test_ai_intent_is_revalidated():
    class MaliciousProvider:
        def interpret(self, text):
            return ProviderResult(Intent("open_application", "powershell.exe"))

    executor = MockExecutor()
    assistant = Assistant(Config(), executor, MaliciousProvider())
    with pytest.raises(ValueError):
        assistant.handle("hello")
    assert executor.calls == []


def test_bounded_history():
    bus = EventBus(2)
    for _ in range(10):
        bus.publish(event("assistant.idle", "test"))
    assert len(bus.snapshot()) == 2


@pytest.mark.parametrize("text", ["", " ", "a" * 4097], ids=["empty", "blank", "oversize"])
def test_input_bound(text):
    with pytest.raises(ValueError):
        Assistant(Config(), MockExecutor()).handle(text)
