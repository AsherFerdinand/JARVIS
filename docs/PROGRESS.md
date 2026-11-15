# Progress

Current version: 0.2.0. Active branch: feat/jarvis-v0.2-voice-ai, based on origin/main fb0dd47
(the merged v0.1 foundation). Core voice/conversation commit: 72143d9.

## Completed milestones

Phase 0/v0.1 foundation preserved: approved registry, isolated OS executor, deterministic routing,
bounded event bus, optional authenticated loopback server, no mandatory third-party runtime.

v0.2 implementation: in-app configurable press/release/cancel activation; lazy optional raw PCM
capture/playback; cloud and mock STT/TTS; English/German hints/aliases; text-only cloud conversation
with bounded memory history; validated state transitions; no overlapping sessions; late-response
cancellation gates; opt-in transcript events; exact legacy event view; diagnostics/benchmarks;
Windows audio-extra packaging with backend-load/mock-voice/DLL/manifest checks.

## Validation — 2026-11-15 Linux cloud

- 120 tests passed, 2 Windows-only checks skipped; no failed/disabled/expected-failure tests.
  Existing v0.1 tests remain passing. New tests exercise synthetic prerecorded WAV, actual capture/
  output adapter code with fake streams, STT multipart/TTS JSON wire formats, provider failures,
  missing configuration, ambiguity/shell denial, history bounds, state transitions, simultaneous
  activation, cancellation during capture/STT/conversation/TTS/playback, legacy/voice contracts,
  and corrupt portable checksum detection. No paid calls or live device streams in tests.
- Ruff lint/format, strict mypy (32 source modules), actionlint 1.7.7 and git diff whitespace passed.
- pip-audit including audio/packaging dependencies: no known vulnerabilities; local unpublished
  jarvis-assistant package cannot be audited against PyPI and was explicitly reported as skipped.
- sdist/wheel built; complete wheel RECORD/hash verification and zero mandatory runtime
  dependencies check passed. Fresh wheel virtualenv ran mock conversation/voice CLI successfully.
- Linux PyInstaller onedir includes the optional sounddevice import; mock voice completed and
  frozen audio backend loaded without streams. Local Linux validation ZIP CRC passed:
  compressed 15,007,374 bytes; extracted logical files 42,299,602 bytes. This is NOT a Windows ZIP.
- Mock voice benchmark: 20 sessions, 31.51 ms sample including max audio fixture allocation,
  last session 0.584 ms, traced allocation peak 3,891,929 bytes, max capture WAV 1,920,044 bytes.
- Linux import sample: core current RSS 16,836 KiB vs core + audio 20,048 KiB (delta 3,212 KiB).
  Not Windows idle memory/CPU, physical stream memory, network latency or a target guarantee.
- Routing sample median 0.003883 ms, p99 0.008116 ms; constructor 0.123518 ms. See PERFORMANCE.md
  for exclusions, dependency sizes, native-library provisioning and measurement limitations.

## Windows CI / artifacts / external blockers

Windows workflow definitions include tests and the full portable ZIP/checksum pipeline, but their
execution result is unconfirmed. GitHub REST API inspection returned Forbidden in this session.
No Windows ZIP availability, compressed/extracted size or hosted check result is claimed.
The only packaged executable actually run here was the Linux validation build.
Git push/PR handoff results are reported at the end of the task; never substitute a saved workflow
or successful source test for a Windows CI result. No cloud environment draft publication needed.

## Known limitations and technical debt

- Live microphone/speaker, Windows GUI effects, real paid STT/TTS/chat endpoints and actual ORBIT
  integration remain unvalidated. No model/voice is hardcoded; chosen provider must support the
  documented JSON/WAV formats and language/rate options. Models and local inference are absent.
- One worker can drain a pending urllib request after cancellation until socket timeout/response;
  no new activation is allowed during that period. Timeout is not a total slow-drip deadline.
  Cancellation cannot reverse an already committed action. No global keyboard hook is installed.
- Exact but incorrectly recognized safe commands remain a provider/hardware risk. Ambiguous,
  negated and multi-command text is not executed; AI replies are plain text only. Sensitive and
  arbitrary shell actions remain unregistered; future sensitive work needs explicit confirmation.
- Events remain bounded snapshots (128 entries) with restart/loss limitations. Default legacy
  channel filters extensions; voice channel carries session metadata, optional transcript only
  with explicit sharing. Local-account malware/availability remains outside the trust boundary.
- Conversation keeps <=6 turns/16k characters in process memory. No audio or history files.
- Default-config JSON in ZIP is informational. Unsigned portable executables remain a trust risk.
- Linux initially lacked PortAudio; a trusted Debian package was verified/extracted locally for
  import measurements. Core and mock tests run without native libraries or the audio extra.

## Next milestone / handoff

Before claiming v0.2 fully validated, inspect successful Windows CI and ZIP checks/artifact metrics
using an authorized GitHub view. v0.3 should address those findings, provider/device recovery and
resource budgets before selecting further features. Keep historical checkpoint A/B hardware gaps
explicit. Do not implement wake word, global hooks or ORBIT changes without a new assigned scope.

User-side Windows installation/testing is NOT required or requested during this milestone.
