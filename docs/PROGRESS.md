# Progress

Version: 0.1.0 foundation. Branch: feat/jarvis-v0.1-foundation.

## Completed
Phase 0 architecture, continuity docs, locked Python tooling, security/performance conventions,
CI definitions. v0.1 text lifecycle and command routing, approved registry/permission boundary,
mock and isolated Windows executors, optional bounded HTTPS AI provider and token usage,
bounded event bus, authenticated read-only localhost snapshots, speech interfaces, opt-in
rotating diagnostics, benchmarks, and Windows ZIP/checksum workflow implemented.

## Validation (2026-11-15, Linux cloud)
- pytest: 49 passed, 1 Windows-only compatibility test skipped; no failed tests.
- Ruff lint and formatting, strict mypy (21 source files), git diff whitespace checks passed.
- pip-audit with packaging group: no known vulnerabilities. Initial pytest 8.3.5 finding
  PYSEC-2026-1845 resolved by pinning reported fixed 9.0.3.
- Wheel/sdist build and wheel RECORD/hash/runtime dependency verification passed; a fresh
  virtual environment installed the wheel and ran mock website/status commands.
- actionlint 1.7.7 passed all workflows. Action commit pins checked against upstream tags.
- Linux PyInstaller onedir built and ran mock status/website smoke tests. About 34 MiB extracted
  on this host (du 34,764 KiB); not a Windows size baseline.
- Benchmark: 10,000 routes, median 0.003349 ms, p99 0.006723 ms, core constructor 0.134514 ms;
  traced peak Python allocations 327,116 bytes including benchmark storage. Excludes imports,
  interpreter startup and OS effects; not process RSS or proof of Windows performance targets.

## Active work and limitations
Foundation implemented; Windows CI/Checkpoint A validation pending. No Windows artifact, real
GUI launch, real API request, Windows hardware resource result, or actual ORBIT integration
has been validated in this cloud session. Speech is interfaces only. Model URL/key/name are
optional and must all be supplied together. No secrets needed for baseline operation.

Git HTTPS read access works. GitHub CLI authentication was reported invalid; branch push and
PR creation are attempted at handoff and their exact outcome is reported separately.

## Known issues / technical debt
- Snapshot history can lose events across 128 entries/restarts; client must deduplicate/reconcile.
- Single HTTP worker can be stalled by a local client until its connection timeout. Local malware
  under the same account is outside the credential trust boundary.
- Application status tracks only launches in the current assistant session.
- Provider compatibility varies; response-format support and real endpoint access untested.
- Portable executables are unsigned. PyInstaller Windows suitability remains provisional.
- Informational default JSON is not a configuration loader. No sensitive/destructive action exists;
  adding one requires a reviewed explicit confirmation design first.

## Next milestone / Windows requirements
Run Windows build CI, inspect downloadable ZIP and checksum/smoke evidence, then complete
Checkpoint A hardware startup, idle CPU/RAM, browser and Notepad checks in RELEASES.md.
Do not request user installation until a successful Windows artifact exists. Subsequent work
should resolve checkpoint A findings before speech (Checkpoint B). Do not modify ORBIT.
