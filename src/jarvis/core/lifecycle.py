import platform
import uuid

from jarvis.actions.permissions import authorize
from jarvis.actions.windows import Executor
from jarvis.config import Config
from jarvis.core.event_bus import EventBus
from jarvis.integration.protocol import event
from jarvis.intelligence.provider import Provider
from jarvis.intelligence.router import Router


class Assistant:
    def __init__(
        self, config: Config, executor: Executor, provider: Provider | None = None
    ) -> None:
        self.config, self.executor, self.provider = config, executor, provider
        self.router = Router(config)
        self.events = EventBus()
        self.running = True
        self.total_tokens: int | None = None
        self.events.publish(event("assistant.idle", str(uuid.uuid4())))

    def handle(self, text: str) -> str:
        if not self.running:
            raise RuntimeError("Assistant stopped")
        if not text.strip() or len(text) > 4096:
            raise ValueError("Command must contain 1–4096 characters")
        self.total_tokens = None
        correlation = str(uuid.uuid4())
        self.events.publish(event("assistant.processing", correlation))
        try:
            intent = self.router.route(text)
            if intent is None and self.provider is not None:
                result = self.provider.interpret(text)
                intent, self.total_tokens = result.intent, result.total_tokens
            if intent is None:
                raise ValueError("Unknown command; no AI provider configured")
            authorize(intent, self.config)
            self.events.publish(event("command.executing", correlation, intent.target))
            match intent.action:
                case "open_website":
                    result_text = self.executor.open_website(
                        self.config.websites[intent.target or ""]
                    )
                case "open_application":
                    target = intent.target or ""
                    result_text = self.executor.open_application(
                        target, self.config.applications[target]
                    )
                case "application_status":
                    result_text = self.executor.application_status(intent.target or "")
                case "system_info":
                    result_text = f"{platform.system()} {platform.release()} ({platform.machine()})"
                case "exit":
                    self.close()
                    result_text = "JARVIS stopped"
                case _:
                    result_text = "JARVIS ready"
            self.events.publish(event("command.completed", correlation, intent.target))
            return result_text
        except Exception:
            self.events.publish(event("command.failed", correlation))
            raise
        finally:
            self.events.publish(event("assistant.idle", correlation))

    def close(self) -> None:
        self.running = False
        self.executor.close()
