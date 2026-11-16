# Controlled Windows validation (v0.5)

This guide prepares a future session; no laptop test, API key or paid request is required for
v0.5 development. Extract the portable ZIP, verify its SHA256 against the adjacent checksum,
and open a terminal in the extracted JARVIS folder. No Python installation, administrator
rights, startup registration or service is needed. Normal startup opens no microphone.
`JARVIS.exe --help` lists the optional checks. Each invocation exits; Ctrl+C cancels active work.
No check saves audio, credentials or history. Redirected stdout can contain text only when
`--show-validation-text` is explicitly selected. Do not redirect private text to shared logs.

## Independent stages

| Purpose | Command | What success establishes |
| --- | --- | --- |
| A configuration | `JARVIS.exe --validate offline` | Locally valid configured provider fields; no HTTP |
| B native backend | `JARVIS.exe --validate backend` | Native library loaded; no stream |
| C devices | `JARVIS.exe --validate devices` | Indices, input/output channels, native rate; no stream |
| D microphone | `JARVIS.exe --validate microphone --allow-microphone --validation-seconds 2` | Bounded capture completed and signal exceeded provisional −55 dBFS RMS threshold |
| E speaker | `JARVIS.exe --validate speaker --allow-playback --validation-seconds 1` | Local playback API completed for a 440 Hz faded tone |
| F STT contract | `JARVIS.exe --validate stt --allow-network` | Synthetic non-speech audio accepted and expected response parsed |
| G conversation | `JARVIS.exe --validate chat --allow-network` | Fixed short question produced a structurally valid reply |
| H TTS | `JARVIS.exe --validate tts --allow-network` | Fixed short text produced bounded PCM16 WAV |
| H with output | `JARVIS.exe --validate tts --allow-network --allow-playback` | Additionally completed the playback API |
| I PTT | `JARVIS.exe --validate interaction --allow-microphone --allow-network --allow-playback` | One bounded activation through configured STT, routing/chat, TTS and playback |

Exit codes: 0 passed, 1 failed, 2 blocked by missing consent, 130 cancelled. JSON contains stage,
sanitized errors, effects and local/request wall timings. A failed cloud configuration does not
block backend/devices/microphone/speaker checks. Missing devices fail safely; enumeration alone
does not prove capture. Capture reports actual PCM format, duration, RMS/peak and clipping;
quiet input reports capture completion separately from insufficient signal. These metrics do
not identify speech or certify microphone quality. Speaker amplitude defaults to .03 full scale,
accepts .005–.1 via `--validation-volume`, and duration never exceeds two seconds. Hardware gain
still affects loudness. API completion is never an audibility claim; actual listening confirmation
belongs in a separately recorded observation. No continuous playback or monitoring is installed.

Set `JARVIS_INPUT_DEVICE` / `JARVIS_OUTPUT_DEVICE` to an index or unique name as in VOICE.md.
`--audio-preflight` provides supported format negotiation without opening streams. Device names
are omitted from the new content-free enumeration report. `--mock-audio` substitutes synthetic
devices only and labels reports `injected_simulation`; network still needs `--allow-network`.

## Providers and privacy

See PROVIDERS.md for exact role endpoints, model/voice fields, capability profiles, TLS rules and
connection/read/total deadlines. Each selected role requires `JARVIS_{STT,AI,TTS}_URL`, `_MODEL`,
`_KEY`; TTS also needs `JARVIS_TTS_VOICE`. Set secrets outside source control for the process only;
no credential file is created. Only explicitly selected live stages contact the configured HTTPS
endpoint, with a cost warning. There are no automatic POST retries. Cancelling kills/reaps the
local request worker; remote processing and billing may continue.

STT defaults to a short synthetic tone, not a person's speech. Empty transcription is a valid
contract-test result; it proves no recognition quality. Providers that reject non-speech must be
recorded as that limitation, not treated as microphone failures. To deliberately upload a bounded
microphone sample, use `--validate stt --validation-source microphone --allow-microphone
--allow-network`. An explicit PCM16 WAV can be selected with `--validation-source file
--validation-file sample.wav`; the same size/format and short duration limits apply. No sample
is stored by default. Network consent alone never enables microphone recording.

PTT starts on the explicit command; Enter releases and `/cancel` cancels (EOF also cancels).
Maximum capture is five seconds; a late Enter cannot extend recording. Default Windows actions
are simulated even in this provider/device interaction. `--allow-actions` separately authorizes
only existing approved registry actions, and only for the interaction stage. AI text never
becomes shell commands. `--no-speak` removes TTS/playback from this stage. Validation remains
standalone: it cannot be combined with commands, voice modes, event server or diagnostic logs.
Existing event endpoints, schemas and authentication are unchanged.

## English and German scenarios

Set `JARVIS_VOICE_LANGUAGE=en` or `de`. STT language hints and TTS rate follow the selected
profile's capabilities; TTS speech language follows the input and selected provider voice.
Test deterministic examples separately: “Open YouTube.”, “Open Notepad.”, “Öffne YouTube.”,
“Öffne Notepad.” Then conversational examples: “Explain regenerative braking.” and
“Was ist Rekuperation?”. Standalone chat/TTS use fixed short English/German prompts. Record
actual transcript accuracy, response language, pronunciation and any model/voice limitation only
from real observations. Canned local HTTPS transcripts test routing and protocol, not language quality.

## Finite resource checkpoint

`JARVIS.exe --validation-benchmark --benchmark-scope user-machine --benchmark-seconds 5`
starts a fresh mock idle child without JARVIS credentials, devices or network. It samples OS CPU,
working set and private memory twice and exits naturally. Sampling interval is bounded to 1–10s.
Windows uses process APIs; other platforms may lack private-memory data. Readiness is polled at
50 ms, so startup includes observer error. A fresh process is not proof of cold disk/cache startup:
`cold_cache_verified` stays false. Record reboot/cache methodology separately if a future session
needs a genuine cold-start comparison. Scope is a user label, not verified hardware provenance.
`--validate backend` measures local native initialization. Microphone and speaker stages report
activation/startup times including enumeration, format checks and stream startup. Provider stages
report aggregate request wall times including worker spawn, TLS, transfer and remote processing;
these cannot isolate pure network latency or remote compute. Interaction reports stage timings,
including AI/routing time. No background telemetry or persistent monitor is installed.

Provisional targets remain <1% idle CPU, <100 MB core RAM, <2s core startup and <50ms routing.
Use matched conditions and several separately invoked samples for hardware conclusions. Hosted
Windows CI labels its own finite samples; it cannot establish laptop performance.

## Evidence boundaries

1. Automated fake devices and local HTTPS: protocol, consent, bounds, cleanup, cancellation,
   redaction and routing only.
2. Windows CI: native load, extracted executable, portable checksum and shared-runner metrics.
3. Actual configured provider account/model: deferred until observed, including billing/quality.
4. Actual microphone/speaker/driver and listening: deferred until observed.
5. Representative laptop resource/latency measurements: deferred until observed.

The final three categories are not acceptance claims for v0.5. No developer/test server, public
fixture CA/key or SDK is bundled in the application. The portable package remains optional-audio,
with no model or GUI dependency. Results and remaining gaps belong in PROGRESS.md.
