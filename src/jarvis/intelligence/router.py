from jarvis.config import Config
from jarvis.intelligence.intent import Intent


class Router:
    def __init__(self, config: Config) -> None:
        self.config = config

    def route(self, text: str) -> Intent | None:
        command = " ".join(text.casefold().strip().rstrip(".!").split())
        aliases = {
            "öffne youtube": "open youtube",
            "öffne notepad": "open notepad",
            "systeminformationen": "system info",
            "zeige systeminformationen": "system info",
        }
        command = aliases.get(command, command)
        simple = {
            "status": "assistant_status",
            "assistant status": "assistant_status",
            "system info": "system_info",
            "show system information": "system_info",
            "exit": "exit",
        }
        if command in simple:
            return Intent(simple[command])
        if command.startswith("open "):
            target = command[5:]
            if target in self.config.websites:
                return Intent("open_website", target)
            if target in self.config.applications:
                return Intent("open_application", target)
        if command.startswith("status ") and command[7:] in self.config.applications:
            return Intent("application_status", command[7:])
        return None
