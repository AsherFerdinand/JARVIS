# JARVIS development instructions

Build a lightweight Windows 11 intelligence/automation engine; ORBIT remains a separate UI.
Before work read this file, docs/ROADMAP.md and docs/PROGRESS.md, inspect Git status,
identify the assigned milestone and review known issues. Work only on the assigned milestone.

## Architecture and conventions
Python 3.12, src layout, typed standard-library runtime, uv.lock, pytest, Ruff, strict mypy.
Reasoning produces intents; registry and permissions validate them before OS effects.
Windows effects remain injectable. No shell tools, arbitrary executable paths, model loading,
telemetry, persistent conversations, microphone capture, or public listeners by default.
Never log secrets or raw commands. Sensitive actions are denied in v0.1; future actions need
explicit user-bound confirmation. Read docs/SECURITY.md before extending capabilities.

Keep history bounded, optional services off, idle paths blocking, and dependencies justified.
Targets: <50 ms routing, <2 s core startup, <1% Windows idle CPU, <100 MB Windows core RAM.
These are provisional; cloud simulations do not establish Windows hardware performance.

## Cloud setup and workflow
Use the existing isolated checkout; do not create a worktree unless explicitly requested.
`UV_CACHE_DIR=/workspace/JARVIS/.cache/uv uv sync --locked` installs the development environment.
Use `uv run jarvis --mock` on Linux; Windows uses `uv run jarvis`.
Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
`uv run pytest -v`, `uv build`, and `uv run python scripts/benchmark.py`.
CI audits dependencies; Windows CI tests and packages with the packaging dependency group.
Use feature branches and PRs; never push directly to main. Do not modify ORBIT.

## Definition of done and continuity
Meaningful tests, lint/types/build pass; security boundaries reviewed; docs updated;
Windows CI versus simulated versus real hardware evidence stated separately.
Update PROGRESS (results, remaining tasks, risks, next milestone), ROADMAP and DECISIONS
when behavior or architecture changes. Do not claim unrun checks or automatic continuation.
For unfinished work record the exact blocker and next command. Finish with a concise handoff.

## v0.2 continuation

Read docs/VOICE.md for explicit voice activation/configuration. Core startup must never import
sounddevice, open audio, start voice threads or upload files automatically. Audio extra only:
`uv sync --locked --extra audio`; native PortAudio also needed on Linux. Windows package builds
must include the extra. `uv run jarvis --mock-voice 'Open YouTube.' --diagnostics` and
`uv run python scripts/benchmark_voice.py` are cloud-safe smokes. Mock audio is synthetic.
All prior lint/type/build commands remain required. Never claim mock audio proves live devices.
Keep one activation worker until cancelled network work drains. Treat AI conversation as plain
text, retain history in memory only, and preserve exact legacy `/v1/events` shape. New voice
fields/types live on `/v1/voice-events`; recognized text sharing defaults off. No wake word,
global keyboard hooks, or ORBIT changes in this milestone. Do not request local Windows tests
for v0.2; record Windows CI, ZIP and hardware evidence separately.

## v0.3 reliability continuation

Provider requests must use the shared isolated transport and obey connection/read/total bounds;
never retry STT/TTS/chat POSTs automatically. Respect the global request slot and process cleanup.
Frozen entry points require multiprocessing.freeze_support(); preserve --check-provider-worker
packaging smoke. Never substitute thread cancellation for proof that a socket/remote work stopped.
The disposable child can be killed locally; remote work/charges can persist. POSIX resource tracker
may remain, but request children must not accumulate. Always call guarded script main functions.

Use `uv run jarvis --health`, `uv run python scripts/benchmark_reliability.py`, and tests with
loopback TLS/synthetic devices. Never request live keys or paid calls for routine validation.
The checked-in localhost key is public test data, not an application credential. Controller close
is terminal/bounded; normal cancel/failure remains recoverable. Defer voice history until completed.
Preserve existing event names/legacy views and sanitize all error codes/health output.

Windows CI rebuilds v0.2 from an ignored source archive for a same-runner size baseline, then
builds v0.3, runs frozen worker/device/mock checks and finite CPU/memory/startup/exit probes.
Inspect its notices, metric artifacts and exact tested SHA. Do not equate hosted results with
representative laptop performance or physical device compatibility. Do not ask for local Windows
testing during v0.3, merge automatically, modify ORBIT, or expand into excluded capabilities.
