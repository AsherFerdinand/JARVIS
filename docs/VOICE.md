# Voice, devices and configuration (v0.4)

Default startup is text-only: no audio stream, sounddevice import, voice worker, model or cloud
request starts automatically. No wake word or global keyboard hook exists. The normal pipeline
is explicit activation → capture → STT → approved command/conversation → TTS → playback.

## Commands

```sh
uv sync --locked
uv run jarvis --mock --command status
uv run jarvis --mock-voice 'Open YouTube.' --diagnostics
uv run jarvis --provider-preflight
uv run jarvis --health
```

Mock voice is fully offline: synthetic PCM, transcript, conversation and playback, including mock
OS actions. --mock alone mocks OS effects only. --mock-audio simulates devices only; configured
providers still receive requests on explicit activation and may charge. It is intended for local
mock HTTP testing, not as a substitute for fully offline --mock-voice.

Real devices additionally need `uv sync --locked --extra audio`; Windows wheels bundle PortAudio,
Linux source use needs a trusted system PortAudio library. `--check-audio-backend` loads the backend
without streams; `--audio-preflight` enumerates/checks candidate PCM formats with streams_opened=0.
`--list-audio-devices` explicitly prints names/indexes. Health/preflight/error reports hide names.
None of these checks establishes a working physical microphone or audible speaker.

## Environment settings (no configuration file)

| Setting | Purpose |
| --- | --- |
| JARVIS_STT_URL / MODEL / KEY | Full HTTPS transcription endpoint, chosen model, secure bearer key |
| JARVIS_TTS_URL / MODEL / KEY | Full HTTPS speech endpoint, chosen model, secure bearer key |
| JARVIS_TTS_VOICE | Explicit string voice identifier supported by that provider/model |
| JARVIS_AI_URL / MODEL / KEY | Optional HTTPS chat-completions conversation provider |
| JARVIS_AI/STT/TTS_TIMEOUT | Response inactivity timeout, default 15 s, >0 and <=120 |
| JARVIS_AI/STT/TTS_CONNECT_TIMEOUT | Connection timeout, default 10 s, capped by response timeout |
| JARVIS_AI/STT/TTS_DEADLINE | Total request deadline including queue/spawn, default 30 s, >0 and <=120 |
| JARVIS_VOICE_LANGUAGE | en (default) or de, STT hint and conversation instruction |
| JARVIS_TTS_RATE | Speaking rate 0.25–4 (default 1), only when declared supported |
| JARVIS_INPUT_DEVICE / OUTPUT_DEVICE | Default when absent; unique name substring/exact name or index:N |
| JARVIS_RECORD_SECONDS | Maximum capture time, default 20, >0 and <=60; byte cap can shorten it |
| JARVIS_SHARE_TRANSCRIPT | 1 explicitly shares recognized text on authenticated voice events; default 0 |

Profiles, supported response formats and optional field/role overrides are described once in
[PROVIDERS.md](PROVIDERS.md). Use --provider-preflight for local configuration errors. Valid syntax
is not live endpoint verification. Inactive/unconfigured providers do not prevent deterministic or
mock commands. Store keys securely outside the repository, never in command-line arguments.
The old informational default-config.json is no longer shipped; environment configuration is consumed.

`uv run jarvis --voice --mock` enables live input/cloud speech with simulated OS actions after
configuration. Type /voice then Enter to activate; speak, then Enter releases (or /cancel cancels).
`--voice-trigger /talk` changes the in-app activation command. Duration/byte limits also stop capture.
During provider work/playback Ctrl+C requests cancellation and exits. Programmatic adapters can
cancel without exiting. `--no-speak` needs no TTS provider or output device. `--voice-file PATH`
explicitly uploads that bounded PCM WAV to STT; it never opens a microphone. No routine tests need
keys, paid endpoints or physical devices, and no user Windows installation/testing is requested now.

## Device selection and PCM negotiation

A fresh PortAudio inventory is queried on each activated capture/playback. Default devices may
change between sessions; explicit selection never falls back to a different default. Ambiguous
names fail; index:N disambiguates host API entries. Explicit adapters pin the first resolved
name/host-API pair and reject an index that later points to a changed identity. PortAudio indices
are not stable hardware serial numbers, and identical labels cannot establish physical identity.
Reselect/create a new adapter after intentional explicit-device changes. No private PortAudio
terminate/reinitialize calls or background device polling are used. Some host API inventories cache
hotplug changes until application restart; this remains a real hardware limitation.

check_input_settings/check_output_settings validate PCM16 before opening streams. Capture prefers
16 kHz mono, then a bounded native/fallback rate (8–48 kHz) and stereo when required. It retains the
negotiated WAV format for STT. Playback prefers the returned rate/channels; if unavailable, bounded
mono/stereo mixing and linear interpolation adapt to a validated device format. These are simple
speech conversions, not high-fidelity anti-aliasing codecs; no MP3/Opus dependency is introduced.
Unsupported settings, missing defaults, unplugged selections and corrupted inventory fail with
sanitized codes. Native start/stop exceptions still trigger an explicit close attempt.

Capture PCM is capped below 4,000,000 bytes, preserving WAV/multipart bounds; at 48 kHz stereo the
cap shortens a 60-second configured limit to about 20.8 seconds. Playback WAV/conversion output
is <=4 MB and <=120 seconds, PCM16 mono/stereo 8–48 kHz. Conversion checks cancellation every
1024 frames. Unsupported/corrupt/truncated WAV fails rather than guessing another encoding.
Audio is transient memory; only synthetic test fixtures use temporary files, removed by the harness.

## Recovery, events and guarantees

States remain idle → listening → transcribing → processing → [executing] → [speaking] → completed,
with failed/cancelled terminals and final idle events. Fresh activation follows normal failures;
concurrent activation is rejected. Capture completion/inactivity is checked only while activated.
One deadline-supervised HTTP child is allowed; cancel terminates/reaps it locally, not remote
provider work/charges. OS scheduling/creation is not hard real-time; cleanup allows <=0.5 s.

Cancelled voice turns do not commit conversation history, including cancellation during TTS.
Clear invalidates pending turns. History remains <=6 turns/16k characters; events <=128. The action
commit gate cannot undo an already committed operation. Controller close is terminal with a bounded
2-second join. A non-cooperative native driver/custom adapter may still need process restart;
unsafe thread termination and replacement-worker accumulation are not used.

Authenticated /v1/events preserves legacy types/fields; /v1/voice-events adds session metadata and
opt-in recognized text. No raw audio or arbitrary provider errors pass through events. Existing
ordering, loss/reconnection semantics remain. `/diagnostics` reports sanitized recent codes and
server status. --diagnostics on a one-shot voice session adds process/traced allocation/worker
counts; these optional measurements add instrumentation overhead and are not hardware proof.

## v0.5 controlled checks

See [VALIDATION.md](VALIDATION.md) for optional independent microphone/synthetic speaker/provider/
PTT checks. Microphone, playback, network and real actions have separate explicit authorization.
Default reports contain only metrics/codes; no recording is saved. Normal voice behavior remains
unchanged. This readiness tooling establishes no actual provider, audibility or laptop result.
