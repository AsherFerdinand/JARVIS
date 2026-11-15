import pytest

from jarvis.core.cancellation import Cancellation, Cancelled
from jarvis.intelligence.conversation import Conversation, MockConversation, Reply
from jarvis.intelligence.provider import ProviderError


def test_context_turn_and_character_limits():
    class Recording(MockConversation):
        messages = []

        def respond(self, messages, cancel):
            self.messages = messages
            return Reply("a" * 4096, 2)

    provider = Recording()
    conversation = Conversation(provider, max_turns=2, max_characters=8192)
    for _ in range(10):
        conversation.respond("q" * 4096, Cancellation())
    assert len(conversation.history) == 1
    assert len(provider.messages) == 2  # system plus current request
    assert conversation.total_tokens == 20
    conversation.clear()
    assert not conversation.history


def test_turn_limit_and_recovery():
    conversation = Conversation(MockConversation(), max_turns=2)
    for text in ["one", "two", "three"]:
        conversation.respond(text, Cancellation())
    assert [q for q, _ in conversation.history] == ["two", "three"]


def test_cancelled_reply_not_retained():
    cancel = Cancellation()

    class LateReply:
        def respond(self, messages, token):
            token.cancel()
            return Reply("too late", 10)

    conversation = Conversation(LateReply())
    with pytest.raises(Cancelled):
        conversation.respond("question", cancel)
    assert not conversation.history
    assert conversation.total_tokens == 0


def test_failed_reply_not_retained():
    class Broken:
        def respond(self, messages, cancel):
            raise ProviderError("failure")

    conversation = Conversation(Broken())
    with pytest.raises(ProviderError):
        conversation.respond("question", Cancellation())
    assert not conversation.history
