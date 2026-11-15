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
