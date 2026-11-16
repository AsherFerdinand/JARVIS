# v0.5 validation readiness

Branch: feat/jarvis-v0.5-validation. Base: ff09385 (complete v0.4, still unmerged;
main remains fb0dd47). Preserve stacked history; PR base feat/jarvis-v0.4-compatibility.

Implemented independent offline/backend/device/capture/tone/STT/chat/TTS/PTT stages, explicit
microphone/playback/network/actions consent, content-free signal metrics and sanitized results.
Production STT remains strict; the synthetic contract probe permits empty text. Validation
Windows actions default to mock execution. No new dependencies, background services or endpoints.
Finite optional CPU/memory/startup benchmark removes provider credentials; local audio activation
and aggregate provider timings are reported separately. Cold cache is not claimed.

New tests cover consent, signal/tone bounds, silence/invalid audio, cancellation, standalone CLI,
redaction, local TLS request/error/worker cleanup, English/German canned routing and finite resource
probes. Existing fake-native stream cleanup and format tests remain. Packaging checks extracted
CLI consent and simulated-device stages plus each provider stage via real loopback TLS. Exact
v0.4 package/resource baseline is rebuilt on the same Windows runner.

Cloud checks: 231 passed, 3 Windows-only skips; Ruff lint/format, strict mypy (41 modules),
wheel/sdist integrity and dependency audit passed. Zero known dependency vulnerabilities (local
unpublished application skipped by PyPI audit). No mandatory runtime dependency was added.

Validation guide: docs/VALIDATION.md. Categories 3 actual providers, 4 physical mic/speaker and
5 representative laptop remain deferred; categories 1 automated simulations and 2 hosted Windows
are recorded below after checks. No paid API, private credential or physical device is required.
No cloud-environment publication/configuration was changed; no branch merge is authorized.

Next milestone recommendation: v0.6 controlled real-account/device observation and recovery
findings, when separately authorized; resolve concrete driver/model/quality issues before new
features. Wake word/hooks/startup/ORBIT/unrestricted control/local models remain outside scope.

---

# Progress

Version: 0.4.0. Branch: feat/jarvis-v0.4-compatibility.
Base: v0.3 commit 07d7e56 (unmerged; main was fb0dd47). Preserve the stacked ancestry; PR base
is feat/jarvis-v0.3-reliability until that milestone merges. Do not merge automatically.

## Implemented

Preserved v0.1–v0.3 actions, text/voice, process deadlines/recovery, bounded history/events and
legacy authenticated endpoints. Baseline reproduced: 157 Linux tests passed, 3 Windows-only skips.

v0.4 reviews official provider/audio APIs, validates configuration offline, declares OpenAI/compatible
wire capabilities, supports explicit JSON/text STT and chat instruction roles, omits unsupported
optional speech fields, and preserves configurable model/voice selection without SDKs.

Audio adapters query/validate fresh inventory and PCM settings per activation; support native rate/
mono/stereo selection, bounded output conversion and identity-bound explicit selection. Default
switch/disconnect/reconnect, Bluetooth-like changes, corrupt/missing devices and native start/stop
cleanup are simulated. There is no private PortAudio restart or background enumeration.

A shared local TLS harness exercises actual STT/action/TTS and STT/chat/TTS requests, errors,
capability differences and cancellation. Tests isolate inherited provider bindings. Extracted ZIP
smokes remove dev environment/Python path, use system-only PATH and verify native load, offline
checks, mock voice, full HTTP pipeline, worker cleanup and SHA256. Informational config JSON is
removed; all documented environment settings are actually consumed.

## Cloud checks (2026-11-16)

- 200 passed, 3 Windows-only skips; no failures, disabled or expected-failure tests. Original
  tests remain passing. New coverage includes offline configuration errors, real local TLS
  provider schemas/auth/rate/server/format/disconnection/cancellation/recovery, chat roles,
  sample-rate/channel conversion, switching/default/explicit device identity and start/stop close.
- Ruff lint/format, strict mypy (37 source modules), actionlint and whitespace checks passed.
- Wheel/sdist RECORD/hash and zero-mandatory-runtime-dependency checks passed; optional audio
  remains sounddevice/CFFI. Dependency audit found no known vulnerabilities; local unpublished
  JARVIS is explicitly skipped by PyPI audit. No vendor SDK, codec framework or model added.
- Linux benchmark samples are recorded in PERFORMANCE.md. No paid credentials, external provider
  calls, physical microphone or speaker were used.

## CI / extracted Windows evidence

Application commit 16635ba passed Linux CI (200 passed, 3 Windows-only skips):
https://github.com/AsherFerdinand/JARVIS/actions/runs/43872874709
and Windows CI (203 passed, zero skips/failures/errors):
https://github.com/AsherFerdinand/JARVIS/actions/runs/43872875094 (2m02s).
The portable JARVIS-0.4.0-windows artifact contains ZIP/checksum and exact current/baseline/resource/
portable-validation JSON. Full manifest/CRC/SHA256 checks and extracted executable smokes passed.

The actual extracted executable ran STT/action/TTS and STT/chat/TTS through real local TLS handlers
with system-only PATH and no dev Python/venv bindings. Both completed with zero surviving request
workers, no paid calls and simulated devices. Backend/worker init, version/text/mock voice, health/
offline preflight also passed. Native enumeration found zero devices and correctly reported missing
default input/output with zero streams, rather than claiming a functioning microphone/speaker.

ZIP/extracted bytes: 10,060,538 / 22,636,271. Same-runner v0.3: 10,044,701 / 22,620,450,
+15,837 / +15,821 bytes (about +0.16% / +0.07%). Windows Server 2022 image 20261112.366.7,
5.0006-second mock-idle sample: working set 28,086,272, private 19,955,712; no measured CPU-time
increase; readiness 383.014 ms, native backend init 48.375 ms, clean natural exit code 0.
Extracted HTTP pipeline peak working set about 32.2 MB and traced peak 4,018,346 bytes, with
instrumentation. PERFORMANCE.md records v0.3 comparisons and limitations; no material size/RAM
regression was observed in these samples, and no laptop acceptance target is claimed.

Public Actions HTML/notices supplied verified statuses, counts and exact metrics. GitHub REST/
GraphQL access is Forbidden; automatic PR creation returned GraphQL Forbidden. Stacked compare:
https://github.com/AsherFerdinand/JARVIS/compare/feat/jarvis-v0.3-reliability...feat/jarvis-v0.4-compatibility?expand=1 Final evidence commit changes documentation only; tested application SHA is 16635ba.
No merge, local laptop test request or cloud environment publication occurred.

## Remaining gaps / next milestone

No live API/account/model/voice or physical Windows 11 microphone/speaker/USB/Bluetooth was
validated. Shared Windows Server 2022 x64 runner and fake devices do not establish laptop targets
or driver behavior. Cached PortAudio host inventories may require restart after hotplug; explicit
identity uses name/host API, not a physical serial number. Linear resampling is speech-oriented,
not a studio-quality codec. WAV PCM16 is required; unsupported formats fail safely.

Previous process/driver caveats remain: cancellation kills local HTTP work but cannot undo remote
processing/charges; an uncooperative driver/custom adapter can require restart after bounded
controller close. Snapshot history is lossy/bounded, conversations transient, builds unsigned and
same-user malware outside the trust boundary. No sensitive/destructive capabilities were added.

Recommend a scoped v0.5 live-provider/device checkpoint based on this matrix/artifact, with explicit
future authorization and hardware requirements; do not add excluded features implicitly. No local
Windows installation/testing or paid keys are required/requested during v0.4.
