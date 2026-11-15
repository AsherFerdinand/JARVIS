# Progress

Current version: 0.3.0. Branch: feat/jarvis-v0.3-reliability.
Base: v0.2 commit 595db1e4ea60146e01e37797702c4bfbd432e4b7; v0.2 was not merged into main when
this task started (main remained fb0dd47). Do not merge automatically. A stacked PR can target
feat/jarvis-v0.2-voice-ai until it is merged; then retarget main as appropriate.

## Completed

Preserved v0.1/v0.2 approved actions, English/German text/voice, optional audio/cloud providers,
mock pipeline and authenticated versioned event views. Baseline: 121 Linux tests passed.

v0.3 adds deadline-supervised standard-library HTTP children, connection/response/total limits,
bounded replies/IPC, cancellation/reaping, one request slot, sanitized HTTP error metadata and
safe-method-only retries. POSTs never replay automatically. Device failures close normal streams
and allow fresh activation; capture detects inactive/completed input, playback preserves primary
errors through cleanup, and chunks use memoryviews. Cancellation no longer blocks on committed
actions; history is staged until completed, clear invalidates old turns, adapters carry session IDs,
shutdown is terminal/bounded, and an event client's partial headers cannot block server close.

Added optional health/config/resource snapshots, recent error codes, bounded mock effect history,
TLS failure/recovery tests, steady-state/starter-process benchmarks, Windows executable probes,
same-runner v0.2 package comparison, checksum/worker/backend/mock smokes, maintained action
pin evaluation and workflow deduplication. No ORBIT/wake-word/hooks/persistence/model additions.

## Cloud validation (2026-11-15)

- 157 tests passed, 3 Windows-only checks skipped; no disabled/expected-failure/failed tests.
  Original test intent remains, with wire mocks injected at the shared transport boundary.
- Real loopback TLS tests cover certificate trust, blocked headers, slow-drip deadline,
  response timeout, socket-worker cancellation/reaping, next-request recovery and controller
  shutdown during a real active request. No paid/external API or physical device is needed.
- Deterministic tests cover HTTP auth/429/5xx/partial/network errors, size/JSON/WAV rejection,
  retry/backoff/capacity bounds, disconnect/missing/init/output cleanup, repeated activation,
  stale callbacks, cancellation before action commit, deferred history and sanitized diagnostics.
- Ruff lint/format, strict mypy (36 source files), actionlint 1.7.7, whitespace and wheel/sdist
  RECORD/runtime-dependency checks passed. Fresh-wheel mock voice/health/worker smokes passed.
- Dependency audit including optional audio/packaging: no known vulnerabilities. The local
  unpublished JARVIS distribution is explicitly skipped by PyPI audit, not represented as audited.
- Current Linux profiling, limitations and baseline comparisons are recorded in PERFORMANCE.md.
  Steady-state 200 synthetic sessions after 128 warmup: retained delta 352 bytes, peak 61,399,
  both histories 128, zero active request workers. This is not a physical-device leak test.

## CI / Windows evidence

Application commit 27fdb80 passed Linux CI (157 passed, 3 skipped):
https://github.com/AsherFerdinand/JARVIS/actions/runs/43759843995
and Windows CI (160 passed, zero failures/errors/skips):
https://github.com/AsherFerdinand/JARVIS/actions/runs/43759843983 (1m21s).
Windows also rebuilt v0.2, verified current executable backend/worker/mock/health smokes,
checksums and resources, and uploaded JARVIS-0.3.0-windows. Final run has three sanitized metric/
test notices and no Node.js deprecation warning; all three action pins declare Node.js 24.

Exact current ZIP/extracted bytes: 10,045,150 / 22,620,450. Same-runner v0.2: 9,641,990 /
22,094,697 (+403,160 / +525,753 bytes, about +4.18% / +2.38%). JSON metrics and baseline/resource
reports are included in the uploaded artifact. Do not confuse the Actions wrapper with the ZIP.

Windows Server 2022 image 20261112.366.7, 5.0004-second mock-idle sample: working set 27,770,880
bytes, private 19,890,176; no measured CPU-time increase; readiness 152.001 ms; backend init
34.836 ms excluding process startup; clean natural exit code 0. PERFORMANCE.md records method,
limits and the distinction from representative laptop/hardware acceptance targets.

Intermediate Windows runs c364127/c6ce20b exposed a two-second incomplete-header shutdown delay.
A sanitized JUnit reporter isolated the unchanged 1.5-second shutdown regression assertion. A
cancellable, 64-KiB/two-second total header reader fixed the Windows timed-read behavior; neither
the assertion nor security checks were relaxed. Added total-header-deadline coverage, and final
Windows/Linux suites pass. Original run 4134dfe was also successful, before exposing this race.

REST/GraphQL API access is Forbidden; public Actions HTML provided verified statuses, test counts
and metric notices. Automatic PR creation returned GraphQL Forbidden. Use the stacked compare link:
https://github.com/AsherFerdinand/JARVIS/compare/feat/jarvis-v0.2-voice-ai...feat/jarvis-v0.3-reliability?expand=1
The final handoff commit updates evidence/documentation only; application CI SHA stays 27fdb80. No merge, local Windows test request or cloud configuration publication occurred.

## Remaining limitations / risks

- Real microphone/speaker/device changes, Windows GUI actions, paid provider behavior and actual
  ORBIT compatibility remain untested. No user-side Windows install/test or live credential request.
- Local HTTP cancellation terminates our process/socket, not remote provider work/charges.
  Deadlines allow <=0.5 seconds process cleanup; OS scheduling/creation is not hard real-time.
- A driver or custom adapter stuck in non-cooperative native code cannot safely be killed as a
  Python thread. Controller close returns after <=2-second join and forbids replacement workers;
  that exceptional case can require process restart. Normal failures/cancellations are reusable.
- The action commit gate cannot reverse an operation already committed before cancellation.
- History/events remain bounded process memory/snapshots, not persistent reliable delivery.
  Default-config JSON remains informational. No sensitive/destructive capability was registered.
- Unsigned executables and same-user malware remain outside distribution/local credential trust.
- POSIX spawn may retain one CPython resource-tracker helper after the first request; Windows
  uses native spawn handles. Request workers are bounded/reaped, with no idle helper preloading.

## Next milestone

Current CI evidence is recorded; scope v0.4 around measured compatibility/provider/device gaps.
Do not add deferred capabilities implicitly. Retain a separate future representative Windows
hardware checkpoint; cloud/TLS/fake devices/shared runners do not prove laptop hardware readiness.
