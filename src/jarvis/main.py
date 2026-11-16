import argparse
import json
import multiprocessing
import os
import sys
import time
import tracemalloc
from pathlib import Path
from threading import Event

from jarvis import __version__
from jarvis.actions.windows import MockExecutor, WindowsExecutor
from jarvis.config import Config
from jarvis.core.lifecycle import Assistant
from jarvis.core.voice_controller import PushToTalkAdapter, VoiceController
from jarvis.diagnostics.health import health
from jarvis.diagnostics.logging import configure
from jarvis.diagnostics.resources import process_resources
from jarvis.integration.server import EventServer
from jarvis.intelligence.conversation import CloudConversation, Conversation
from jarvis.intelligence.preflight import preflight
from jarvis.intelligence.provider import ProviderError
from jarvis.intelligence.transport import ProcessTransport
from jarvis.speech.audio import AudioError
from jarvis.speech.audio_devices import audio_backend, audio_preflight, list_devices
from jarvis.speech.session import State
from jarvis.speech.setup import endpoint_from_environment, make_voice


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS text assistant")
    parser.add_argument("--mock", action="store_true", help="Use simulated OS actions")
    parser.add_argument("--command", help="Execute one command then exit")
    parser.add_argument("--events-port", type=int, help="Enable optional loopback event server")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--diagnostics", action="store_true", help="Report token usage and event count"
    )
    parser.add_argument("--log-file", type=Path, help="Opt-in bounded diagnostic log")
    voice_mode = parser.add_mutually_exclusive_group()
    voice_mode.add_argument("--voice", action="store_true", help="Enable in-app push-to-talk")
    voice_mode.add_argument("--voice-file", type=Path, help="Explicitly transcribe a PCM WAV file")
    voice_mode.add_argument(
        "--mock-voice", help="Run synthetic voice interaction without devices/API"
    )
    parser.add_argument("--voice-trigger", default="/voice", help="In-app activation command")
    parser.add_argument("--no-speak", action="store_true", help="Disable speech output")
    parser.add_argument("--list-audio-devices", action="store_true")
    parser.add_argument(
        "--check-audio-backend", action="store_true", help="Load audio without streams"
    )
    parser.add_argument(
        "--health", action="store_true", help="Sanitized configuration/resource report"
    )
    parser.add_argument(
        "--check-provider-worker", action="store_true", help="Check isolated provider runtime"
    )
    parser.add_argument(
        "--idle-probe", type=float, help="Explicit bounded idle measurement interval"
    )
    parser.add_argument(
        "--provider-preflight", action="store_true", help="Offline provider checks; no requests"
    )
    parser.add_argument(
        "--audio-preflight", action="store_true", help="Check device formats without streams"
    )
    parser.add_argument(
        "--mock-audio",
        action="store_true",
        help="Simulate devices only; configured provider requests may incur charges",
    )
    args = parser.parse_args()
    server = None
    assistant = None
    controller: VoiceController | None = None
    try:
        logger = configure(args.log_file)
        logger.info("Assistant starting")
        if args.provider_preflight:
            report = preflight()
            print(json.dumps(report, indent=2))
            return 0 if report["valid_configured_providers"] else 1
        if args.audio_preflight:
            print(
                json.dumps(
                    audio_preflight(
                        os.getenv("JARVIS_INPUT_DEVICE"), os.getenv("JARVIS_OUTPUT_DEVICE")
                    )
                )
            )
            return 0
        if args.mock_audio and not (args.voice or args.voice_file):
            raise ValueError("Mock audio requires an explicit voice activation mode")
        if args.mock_audio:
            print(
                "Audio devices simulated; configured provider requests may incur charges.",
                file=sys.stderr,
            )
        if args.health:
            print(json.dumps(health(probe_audio=args.check_audio_backend), indent=2))
            return 0
        if args.check_provider_worker:
            ProcessTransport().probe()
            print("Provider worker available")
            return 0
        if args.check_audio_backend:
            started = time.perf_counter()
            audio_backend()
            elapsed = (time.perf_counter() - started) * 1000
            print("Audio backend available; no stream opened")
            if args.diagnostics:
                print(json.dumps({"audio_backend_init_ms": elapsed}))
            return 0
        if args.list_audio_devices:
            print(list_devices())
            return 0
        if not args.voice_trigger.strip() or len(args.voice_trigger) > 32:
            raise ValueError("Invalid activation command")
        if args.command is not None and (
            args.voice or args.voice_file or args.mock_voice is not None
        ):
            raise ValueError("Select text command or voice mode")
        conversation = None
        if args.mock_voice is None and any(
            os.getenv(name) for name in ("JARVIS_AI_URL", "JARVIS_AI_MODEL", "JARVIS_AI_KEY")
        ):
            conversation = Conversation(
                CloudConversation(endpoint_from_environment("JARVIS_AI")),
                language=os.getenv("JARVIS_VOICE_LANGUAGE", "en"),
            )
        executor = MockExecutor() if args.mock or args.mock_voice is not None else WindowsExecutor()
        assistant = Assistant(Config(), executor, conversation=conversation)
        if args.voice or args.voice_file or args.mock_voice is not None:
            controller = make_voice(
                assistant,
                mock_text=args.mock_voice,
                audio_file=args.voice_file,
                speak=not args.no_speak,
                mock_audio=args.mock_audio,
            )
        if args.events_port is not None:
            server = EventServer(
                assistant.events, os.getenv("JARVIS_EVENT_TOKEN", ""), args.events_port
            )
            server.start()
            print(f"Event channel: 127.0.0.1:{server.port}")
        if args.idle_probe is not None:
            if not 0 < args.idle_probe <= 30 or controller is not None or args.command is not None:
                raise ValueError("Idle probe requires standalone text mode, 0–30 seconds")
            print("JARVIS ready", flush=True)
            Event().wait(args.idle_probe)
            return 0
        if args.voice_file or args.mock_voice is not None:
            if controller is None:
                raise ValueError("Voice not configured")
            if args.diagnostics:
                tracemalloc.start()
            controller.start()
            result = controller.wait()
            print(
                result.response
                if result.state.current == State.COMPLETED
                else result.error_code or result.state.current
            )
            if args.diagnostics:
                print(
                    json.dumps(
                        {
                            "state": result.state.current,
                            "total_tokens": result.total_tokens,
                            "timings_ms": result.timings_ms,
                            "python_peak_bytes": tracemalloc.get_traced_memory()[1],
                            "process": process_resources(),
                            "active_request_workers": len(multiprocessing.active_children()),
                        }
                    )
                )
            return 0 if result.state.current == State.COMPLETED else 1
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
                    if text == "/diagnostics":
                        print(
                            json.dumps(
                                health(
                                    events=assistant.events,
                                    event_port=server.port if server else None,
                                )
                            )
                        )
                        continue
                    if controller is not None and text == args.voice_trigger:
                        adapter = PushToTalkAdapter(controller)
                        adapter.press()
                        try:
                            release = input("Listening; Enter releases, /cancel cancels: ")
                        except EOFError:
                            adapter.cancel()
                        else:
                            if release == "/cancel":
                                adapter.cancel()
                            else:
                                adapter.release()
                        result = controller.wait()
                        print(
                            result.response
                            if result.state.current == State.COMPLETED
                            else result.error_code or result.state.current
                        )
                        continue
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
                except (ValueError, RuntimeError, OSError, ProviderError, AudioError):
                    logger.warning("Command failed")
                    print("Command failed; check command or provider configuration")
        return 0
    except (ValueError, RuntimeError, OSError, ProviderError, AudioError):
        print("JARVIS failed; check platform, command, or provider configuration")
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        if controller is not None:
            controller.close()
        if server is not None:
            server.close()
        if assistant is not None:
            assistant.close()
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        configure(None)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
