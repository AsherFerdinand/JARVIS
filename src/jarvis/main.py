import argparse
import json
import os
from pathlib import Path

from jarvis.actions.windows import MockExecutor, WindowsExecutor
from jarvis.config import Config
from jarvis.core.lifecycle import Assistant
from jarvis.diagnostics.logging import configure
from jarvis.integration.server import EventServer
from jarvis.intelligence.provider import OpenAIProvider, ProviderError


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS text assistant")
    parser.add_argument("--mock", action="store_true", help="Use simulated OS actions")
    parser.add_argument("--command", help="Execute one command then exit")
    parser.add_argument("--events-port", type=int, help="Enable optional loopback event server")
    parser.add_argument("--version", action="version", version="0.1.0")
    parser.add_argument(
        "--diagnostics", action="store_true", help="Report token usage and event count"
    )
    parser.add_argument("--log-file", type=Path, help="Opt-in bounded diagnostic log")
    args = parser.parse_args()
    server = None
    assistant = None
    try:
        logger = configure(args.log_file)
        logger.info("Assistant starting")
        url, model, key = (
            os.getenv(name) for name in ("JARVIS_AI_URL", "JARVIS_AI_MODEL", "JARVIS_AI_KEY")
        )
        provider = None
        if any((url, model, key)):
            if not all((url, model, key)):
                raise ValueError("Set all JARVIS_AI_URL, JARVIS_AI_MODEL and JARVIS_AI_KEY")
            provider = OpenAIProvider(
                url or "", model or "", key or "", float(os.getenv("JARVIS_AI_TIMEOUT", "15"))
            )
        assistant = Assistant(
            Config(), MockExecutor() if args.mock else WindowsExecutor(), provider
        )
        if args.events_port is not None:
            server = EventServer(
                assistant.events, os.getenv("JARVIS_EVENT_TOKEN", ""), args.events_port
            )
            server.start()
            print(f"Event channel: 127.0.0.1:{server.port}")
        if args.command is not None:
            print(assistant.handle(args.command))
            if args.diagnostics:
                print(
                    json.dumps(
                        {
                            "total_tokens": assistant.total_tokens,
                            "event_count": len(assistant.events.snapshot()),
                        }
                    )
                )
        else:
            while assistant.running:
                try:
                    text = input("JARVIS> ")
                except EOFError:
                    break
                try:
                    print(assistant.handle(text))
                    if args.diagnostics:
                        print(
                            json.dumps(
                                {
                                    "total_tokens": assistant.total_tokens,
                                    "event_count": len(assistant.events.snapshot()),
                                }
                            )
                        )
                except (ValueError, RuntimeError, OSError, ProviderError):
                    logger.warning("Command failed")
                    print("Command failed; check command or provider configuration")
        return 0
    except (ValueError, RuntimeError, OSError, ProviderError):
        print("JARVIS failed; check platform, command, or provider configuration")
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        if server is not None:
            server.close()
        if assistant is not None:
            assistant.close()
        configure(None)


if __name__ == "__main__":
    raise SystemExit(main())
