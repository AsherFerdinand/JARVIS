# Development

Read AGENTS.md and continuity docs first. Python 3.12 and uv; `uv sync --locked`.
Cloud cache if home is read-only: `export UV_CACHE_DIR=/workspace/JARVIS/.cache/uv`.
`uv run jarvis --mock --command status` is a deterministic smoke test; no secrets required.

Required: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
`uv run pytest -v`, `uv build`. `uv run pip-audit --progress-spinner off` audits the environment.
`uv run python scripts/benchmark.py` measures portable routing. Do not modify uv.lock incidentally;
explicit dependency changes use uv lock and review. CI runs unit/integration/contract tests together.

Windows: `uv sync --locked --group packaging`, then `uv run python scripts/package_windows.py`.
The script builds onedir, smokes mock status and native system info, creates manifests and ZIP.
OS-side browser/GUI interaction remains a hardware checkpoint; tests mock process launches.

AI provider uses all three JARVIS_AI_URL/MODEL/KEY environment settings; basic tests mock transport.
Never add production credentials to test fixtures. Optional event server requires EVENT token per README.
No services need startup for the default development/test workflow. Exit CLI with exit, EOF or Ctrl+C.

Artifact integrity: after `uv build`, run `uv run python scripts/check_package.py`.
Workflow validation uses actionlint 1.7.7. Third-party action revisions were checked against upstream tags.
`--diagnostics` reports token/event counts; `--log-file PATH` enables bounded fixed-message logging.
No log file is written by default. Provider timeout can use JARVIS_AI_TIMEOUT (0–120 seconds,
exclusive lower bound); this is a socket timeout, not a guaranteed total wall-clock deadline.

## v0.2

See VOICE.md for cloud/device settings and the in-app press/release alternative. Baseline tests
need no devices, credentials, audio extra or native libraries. `uv run jarvis --mock-voice
'Open YouTube.' --diagnostics` validates the synthetic pipeline. `uv run python
scripts/benchmark_voice.py` reports mock timings, bounded audio allocation and optional import
memory; use `uv run --extra audio` plus native PortAudio to measure the actual audio import.
Linux uses system PortAudio; Windows wheels bundle it. Tests do not make paid API requests.
Windows CI installs `--extra audio --group packaging`, tests native import without streams,
then verifies the frozen backend, mock voice, DLL, ZIP contents and SHA256 manifest.

## v0.3

`uv run jarvis --health` needs no platform executor, credentials or native audio library. It reports
presence/status only; --health --check-audio-backend explicitly probes native loading. `/diagnostics`
adds current event-server state and recent sanitized codes. `--check-provider-worker` performs a
bounded spawn/IPC smoke with no network. New transport integration tests run their own loopback
TLS server and trust only its fixture CA; no external/paid API or physical audio device is needed.

`uv run python scripts/benchmark_reliability.py` stresses 200 synthetic sessions and measures spawn
cost, bounded histories and retained allocations. It is not a hardware or real-provider benchmark.
All original lint/type/test/build/package-integrity/audit commands remain required.
