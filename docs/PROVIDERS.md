# Provider contracts and offline validation

Reviewed 2026-11-16 against [OpenAI's official OpenAPI schema](https://github.com/openai/openai-openapi/blob/master/openapi.yaml)
and [sounddevice 0.5.3 source/API documentation](https://github.com/spatialaudio/python-sounddevice/blob/0.5.3/sounddevice.py).
Reviewed source SHA256: OpenAPI `e2351db74af852fffea9d20de711d778619fd1e0cdbb1d091eec6d37f22908d2`;
sounddevice `db3bfdb3b71c934a6fb169aab41e61a90fd1d1491aa03fccc97e8e895d3c2b58`.
Documentation and local simulations do not prove live account, endpoint, model or voice availability.
No paid/live provider probe is implemented in preflight, and no vendor SDK is required.

| Role | Implemented request/response contract | Limits and explicit differences |
| --- | --- | --- |
| STT | HTTPS POST `/v1/audio/transcriptions`; bearer auth; multipart model, response_format, optional language and `file` named speech.wav with audio/wav MIME | json object with text, or explicit UTF-8 text response; en/de hints; <=4096 characters; bounded PCM16 WAV input |
| TTS | HTTPS POST `/v1/audio/speech`; bearer auth; JSON model/input/voice/response_format=wav, optional speed | String voice IDs; WAV PCM16 mono/stereo, 8–48 kHz, <=4 MB/120 s; rate 0.25–4 only when capability enabled |
| Chat | HTTPS POST `/v1/chat/completions`; bearer auth; JSON model/messages | Non-streamed choices[0].message.content must be a string; usage.total_tokens optional; <=4096 response characters; no tools |
| Other APIs | Replaceable ChatProvider/Transcriber/Synthesizer interfaces | Responses API, streaming, arbitrary auth schemes, custom voice objects, MP3/Opus decoding and Azure-style key/query auth are not implemented by this adapter |

Models and voices must be explicitly configured; there is no selected default model. Known
schema restrictions are validation data, not model choices: documented gpt-4o-transcribe and
mini/snapshot families require JSON transcription. Other models may differ. TTS has no language
field in this API: response text and voice determine language; conversations receive the chosen
language instruction and approved German commands have German spoken confirmations.

Two role-specific profiles are available through JARVIS_AI/STT/TTS_PROFILE:

- `openai` (default) sends the documented optional STT language and TTS speed fields.
- `compatible` conservatively omits both optional fields; it still requires the declared bearer,
  multipart/chat and WAV contracts. A nondefault speaking rate is rejected unless explicitly enabled.

JARVIS_STT_LANGUAGE_HINT=0/1 and JARVIS_TTS_SPEED=0/1 override those capabilities for a documented
server. JARVIS_STT_RESPONSE_FORMAT is json (default) or text; JARVIS_TTS_FORMAT must be wav.
JARVIS_AI_SCHEMA must be chat_completions. JARVIS_AI_SYSTEM_ROLE is system (default), developer,
or none, adapting only the instruction message; none loses language/style instructions. A custom
HTTPS path is used literally with an unverified-path warning. Incorrect api.openai.com role paths
are rejected. URL credentials/query/fragment forms are rejected by environment preflight.
Unknown model/voice support is never inferred from an OpenAI-like hostname or response shape.

`--provider-preflight` validates locally and reports sanitized codes for missing URL/key/model,
partial configuration, unsupported format/schema/profile/language/rate/role and invalid timeouts.
No requests or native audio initialization occur. The overall flag refers only to configured
providers; all-unconfigured is valid for offline/deterministic use, while each inactive role still
lists its missing requirements. `live_verified` remains false even when local syntax is valid.

Actual requests retain connection/read/total deadlines, HTTPS/hostname validation, blocked redirects,
bounded results and process cleanup. POSTs never retry automatically. No error body, endpoint,
model/key value or input text is included in preflight diagnostics or failure events. Real speech
requires explicit --voice activation or --voice-file. --mock-audio simulates devices ONLY and still
uses configured HTTP providers; it warns about possible charges. --mock-voice is fully offline.

The local TLS harness validates these contracts through actual requests and worker processes,
including STT → approved action → TTS and STT → conversation → TTS, failure/recovery/cancellation
and optional-field differences. It uses public synthetic credentials/audio and a fixture CA, keeps
certificate checks on, and never contacts a paid service. Hardware compatibility remains unproven.
