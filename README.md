# JARVIS 0.2.0

A lightweight Windows text assistant and future ORBIT automation engine. Mandatory runtime dependencies:
Python standard library only; device audio is an optional extra. No local model, automatic microphone capture, or telemetry.

```sh
uv sync --locked
uv run jarvis --mock --command "open youtube"
uv run jarvis --mock
```

On Windows omit `--mock` for approved browser/Notepad actions. Commands: `open youtube`,
`open notepad`, `status notepad`, `system info`, `status`, `exit`. Application status covers
only processes launched in this session; it is not a global process inventory.

Optional AI: set `JARVIS_AI_URL` to an HTTPS chat-completions endpoint, `JARVIS_AI_MODEL`,
and `JARVIS_AI_KEY` securely. No key is needed for deterministic commands. Provider output
is revalidated against the registry and never executed as a shell command.

Optional ORBIT events: set a random `JARVIS_EVENT_TOKEN` (at least 32 ASCII characters),
then `uv run jarvis --mock --events-port 8765`. This exposes a read-only loopback snapshot.
See [architecture](docs/ARCHITECTURE.md), [development](docs/DEVELOPMENT.md),
[security](docs/SECURITY.md), [progress](docs/PROGRESS.md), and [Windows ZIP guide](docs/RELEASES.md).

Linux tests validate mocks and contracts. Windows compilation/packaging requires Windows CI;
representative hardware resource targets are not yet validated.

Diagnostics: `--diagnostics` reports the latest command token count (null for local routing)
and bounded event count. `--log-file PATH` opts into rotating fixed-message logs (3 × 256 KB).
`JARVIS_AI_TIMEOUT` sets the provider socket timeout in seconds (default 15, maximum 120).

## Optional voice and conversation

`uv run jarvis --mock-voice 'Open YouTube.' --diagnostics` runs the entire synthetic voice
pipeline without devices or paid calls. Cloud speech and live audio require explicit provider
configuration and activation; see [VOICE.md](docs/VOICE.md). Conversation requests now return
bounded text responses; known commands still bypass AI. No wake word or global keyboard hooks.
Windows CI builds a self-contained v0.2 portable ZIP including optional PortAudio runtime;
its execution and hardware compatibility must be reported separately from cloud mocks.
