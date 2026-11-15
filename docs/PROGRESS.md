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

- 155 tests passed, 3 Windows-only checks skipped; no disabled/expected-failure/failed tests.
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

Application commit 4134dfe passed Linux CI:
https://github.com/AsherFerdinand/JARVIS/actions/runs/43758145286
and Windows tests, baseline/current packaging, executable smokes, checksum and resource checks:
https://github.com/AsherFerdinand/JARVIS/actions/runs/43758145275 (1m23s).
JARVIS-0.3.0-windows is listed on that run. Sanitized public notices expose exact metrics without
confusing the Actions wrapper with the application ZIP. ZIP 10,043,980 bytes; extracted 22,619,590.
Same-runner v0.2: ZIP 9,641,975 / extracted 22,094,697 bytes (+4.17% / +2.38% respectively).

Hosted Windows five-second mock-idle sample: working set 27,922,432 bytes, private 19,755,008,
no measured CPU-time increase, readiness 152.294 ms, clean natural exit code 0. See PERFORMANCE.md
for exact method, OS/image, timing limits and why this does not establish laptop targets.

That first run still warned about upload-artifact v5 using Node.js 20. Its verified Node.js 24 v6
replacement and separate internal backend-init timing are being revalidated on the final branch.
REST/GraphQL API access was previously Forbidden; public Actions HTML is a working status/notice
fallback. PR attempt/result and final checked SHA are recorded at task handoff. No merge or cloud
configuration publication has been performed.

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

Finalize current CI evidence, then scope v0.4 around measured compatibility/provider/device gaps.
Do not add deferred capabilities implicitly. Retain a separate future representative Windows
hardware checkpoint; cloud/TLS/fake devices/shared runners do not prove laptop hardware readiness.
