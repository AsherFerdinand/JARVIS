# Voice and conversation v0.2

Default startup is text-only. No speech model, microphone stream, audio backend, or voice worker
is loaded until explicitly requested. There is no wake word, global hook, or background recorder.

## Reproducible cloud development

```sh
uv sync --locked
uv run jarvis --mock-voice 'Open YouTube.' --diagnostics
uv run jarvis --mock-voice 'Explain regenerative braking.' --diagnostics
uv run pytest -q
uv run python scripts/benchmark_voice.py
```

Mock voice uses tiny synthetic PCM (not a recording of a person), a deterministic transcript,
mock cloud conversation and mock playback. It never calls a paid endpoint or accesses devices.
`--mock` controls OS effects; `--mock-voice` also forces mock OS effects even on Windows.

## Explicit cloud/device activation

Install `uv sync --locked --extra audio` for real device input/output. Windows wheels provide
PortAudio; source development on Linux additionally needs a trusted system PortAudio library.
The portable Windows build includes this optional runtime without development tools or models.

Set these environment settings securely before enabling voice (never commit values):

| Setting | Purpose |
| --- | --- |
| JARVIS_STT_URL / MODEL / KEY | Full HTTPS transcription endpoint, model and bearer key; all required |
| JARVIS_STT_TIMEOUT | Socket timeout seconds, default 15, >0 and <=120 |
| JARVIS_TTS_URL / MODEL / KEY | Full HTTPS speech endpoint, model and bearer key; required unless --no-speak |
| JARVIS_TTS_VOICE | Explicit provider voice identifier; required with speech output |
| JARVIS_TTS_RATE | Provider speaking speed, 0.25–4, default 1 |
| JARVIS_TTS_TIMEOUT | Socket timeout seconds, default 15, >0 and <=120 |
| JARVIS_AI_URL / MODEL / KEY | Optional full HTTPS chat-completions endpoint for non-command conversations |
| JARVIS_AI_TIMEOUT | Chat socket timeout seconds, default 15, >0 and <=120 |
| JARVIS_VOICE_LANGUAGE | en (default) or de; STT language hint and conversation response language |
| JARVIS_RECORD_SECONDS | Maximum capture duration, default 20, >0 and <=60 |
| JARVIS_INPUT_DEVICE / OUTPUT_DEVICE | Optional PortAudio device name; defaults to system device |
| JARVIS_SHARE_TRANSCRIPT | 1 explicitly shares recognized text on authenticated voice event channel; default 0 |

For OpenAI, full paths are `/v1/audio/transcriptions`, `/v1/audio/speech`, and
`/v1/chat/completions` on `https://api.openai.com`; no endpoint or model is assumed in code.
Use models supporting JSON transcription and WAV speech. Formats were checked against
[OpenAI's published OpenAPI schema](https://github.com/openai/openai-openapi/blob/master/openapi.yaml)
on 2026-11-15. STT uses multipart model/language/response_format=json/file(speech.wav).
TTS uses JSON model/input/voice/response_format=wav/speed. TTS has no documented language
field: language follows the input text and selected voice. Known German commands receive
German spoken confirmations; system/application status may include technical OS/executor strings. Model/voice/language/speed support
varies by provider; live endpoint compatibility is not claimed by mocked contract tests.

```sh
uv run jarvis --voice --mock
```

Type `/voice` then Enter to activate the microphone. Speak, then press Enter to release it.
`/cancel` at the recording prompt cancels instead. The duration limit also stops capture.
`--voice-trigger /talk` changes the activation command. This in-app press/release adapter is
intentional: no remotely unvalidated global keyboard hook is installed. Future global shortcuts
can call the same PushToTalkAdapter after consent and Windows validation.

During transcription, conversation or playback, Ctrl+C requests cancellation and exits the CLI.
Programmatic adapters can call controller.cancel() without exiting. A second session is rejected
while the first is running/draining. Socket requests cannot be forcibly aborted by urllib;
late results are discarded, and their single worker must drain before another activation.
Socket timeouts are not strict total wall-clock deadlines against a slow-drip remote server.
A side effect already committed before cancellation cannot be undone.

`--voice-file PATH --no-speak --mock` explicitly uploads a bounded prerecorded PCM16 WAV to the
configured STT endpoint without opening a microphone or speaker. Omit --no-speak only when
cloud TTS and an output device are configured. This is not an automatic file upload.
`--list-audio-devices` queries devices explicitly; `--check-audio-backend` loads the optional
backend without opening streams. Device failures produce safe generic error codes.

## Bounds and safety

PCM16 mono capture is 16 kHz; <=60 seconds (1,920,000 PCM bytes). All WAV input/output is capped
at 4,000,000 bytes, with 8–48 kHz PCM16 mono/stereo playback, <=120 seconds. Multipart/validation
can make bounded temporary copies. WAV streaming-length sentinels are supported under the
same byte limit; truncated regular WAVs are rejected. Silence/empty transcripts fail safely.
Text/transcripts/replies are <=4096 characters. Conversation history holds <=6 turns and
<=16,000 characters, in memory only; failed/cancelled provider replies are not appended.

Known commands (including trailing periods/exclamation marks and documented German aliases)
use the same registry and executor as text mode. Questions, negation and multi-command phrases
are not fuzzy-matched into actions. Unknown voice requests can become plain-text conversations;
AI reply text never becomes an executable intent. Unsupported/sensitive capabilities remain denied.
No STT confidence guarantee is claimed; an exact but incorrectly recognized safe command remains
a hardware/provider risk. No destructive command is registered.

## States and events

idle → listening → transcribing → processing → [executing] → [speaking] → completed.
Any nonterminal state may transition to failed/cancelled; terminals cannot restart. New activation
creates a fresh session. Capture/playback own device context managers. Cancellation is checked
at every phase and atomically gates action execution and conversation history commits.

`/v1/events` preserves the v0.1 event types and field shape. Authenticated `/v1/voice-events`
adds session_id and optional recognized_text/error_info plus transcribing, transcription completed,
session completed/failed/cancelled and playback completed/cancelled events. Session events and
command events share session/correlation IDs. No raw audio or arbitrary exception text is emitted.
Speech is shown as speaking during synthesis/playback; playback completion means the output
stream finished, not proof that a physical speaker was audible. Existing snapshot retention and
reconnection limitations still apply. Consumers of the extended channel must ignore unknown fields/types.
