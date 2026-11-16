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

- 199 passed, 3 Windows-only skips; no failures, disabled or expected-failure tests. Original
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

Application commit 990e3f2 passed Linux CI (198 passed, 3 skips):
https://github.com/AsherFerdinand/JARVIS/actions/runs/43870557125
and Windows CI (201 passed, no skips/failures):
https://github.com/AsherFerdinand/JARVIS/actions/runs/43870557107 (2m04s).
It produced JARVIS-0.4.0-windows with verified manifest/checksum and all extracted smokes.
Both complete local TLS provider paths ran in the actual extracted executable with no dev
bindings, zero surviving request workers and no paid calls/audio streams. Native backend loaded;
the runner enumerated zero audio devices, correctly reported missing input/output, and did not
pretend to validate a physical device. Metrics/validation JSON are included with the ZIP.

That run measured ZIP 10,058,325 / extracted 22,634,267 bytes versus same-runner v0.3
10,045,690 / 22,620,450 (+12,635 / +13,817 bytes). Working set 28,180,480, private 19,865,600,
no measured CPU-time increase over five idle seconds, 329.929 ms readiness, 42.555 ms native
backend init. Baseline and measurement limits are detailed in PERFORMANCE.md.

Final documentation and additional fail-closed default-index/configuration guards are being
revalidated on the final branch SHA. Public Actions HTML/notices supply verified results when
GitHub REST/GraphQL is Forbidden. Final PR attempt/result is recorded at handoff. No merge,
local laptop test request or cloud environment publication occurred.

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
