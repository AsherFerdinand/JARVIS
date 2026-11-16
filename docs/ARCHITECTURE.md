# Architecture

CLI → deterministic router → optional provider → intent → registry/permission boundary → executor.
Lifecycle publishes structured events to a locked bounded deque (128 events). Optional single
HTTP service reads snapshots. No permanent worker beyond that opt-in service; no polling core.
Shutdown releases assistant/server resources and leaves user applications open.

## ORBIT protocol v1
GET `/v1/events` on IPv4 127.0.0.1 only; `Authorization: Bearer <token>` required.
Token is supplied via environment, never returned or logged; no CORS or remote binding.
Response `{version: 1, events: [...]}` contains events with version, UUID id, epoch timestamp,
correlation_id, event, application, display_text, icon and progress. Nullable fields are explicit.
Event types: assistant.idle/listening/processing/speaking and command.executing/completed/failed.
Only idle/processing/command events are emitted in the text milestone.

Order is deque publication order, not timestamp order. Command events share a correlation UUID.
Client deduplicates by event id, reconnects using bounded exponential backoff (1–30 seconds),
and fetches a new snapshot. History may be lost after 128 events or restart; this is a status
channel, not a reliable task ledger. IDs change on restart. No command ingress exists.
401 means invalid credential; 404 invalid path; timeout/reconnect requires a fresh snapshot.
Poll only while a UI consumer is active, at a low frequency (e.g. 1 second); no core polling.
Single server limits threads and connection timeout bounds stalled clients; malicious local
clients can still deny service. FastAPI/WebSockets are deferred until measured demand.

In v0.1, speech protocols described STT/TTS/wake-word/microphone/output boundaries only.
v0.2 implementations are described below. No local speech model is selected or bundled. Future Ollama support can implement Provider;
no local model or provider daemon is started now.

## v0.2 voice extension

The speech pipeline now has cancellable Capture/Transcriber/Synthesizer/Playback ports in
speech/ports.py; byte-only v0.1 interfaces remain import-compatible. VoiceController owns one
optional activation worker and an explicit SessionState. Its in-app PushToTalkAdapter exposes
press/release/cancel; no global hotkey implementation is installed. Sounddevice raw PCM streams
are loaded lazily and context-managed, with bounded in-memory WAV buffers. Cloud audio transport
uses standard-library HTTPS; no SDK/model loads at startup.

Deterministic recognized commands reuse Assistant/registry/executor. Unknown requests use a
bounded Conversation that returns text only, not tools. The optional legacy intent provider
remains available to programmatic v0.1 consumers. Text CLI now uses conversational fallback.
Cancellation discards late remote results and serializes action commits; it cannot undo an
already committed OS action or forcibly interrupt an active urllib socket request.

The extended `/v1/voice-events` view exposes session IDs and additive voice types. `/v1/events`
filters new types/fields for exact legacy compatibility. Both use the same loopback authentication.
Recognized text sharing is off by default. See VOICE.md for configuration, bounds and transitions.
The earlier interfaces-only statement describes v0.1; cloud/mock/device adapters now exist.

## v0.3 hardening

All provider paths, including legacy intent interpretation, share intelligence/transport.py and
sanitized ProviderError metadata. No client/worker starts on import. A single global slot supervises
short-lived standard-library spawn workers via a private local pipe; endpoint data/credentials are
passed through IPC, never process command-line arguments or files. Parent deadlines include queue
wait and worker startup; cancellation or deadline terminates the local child and closes its socket.
No claim is made about undoing remote processing. Request/body size limits apply before IPC return.
Safe GET/HEAD retries are bounded; actual STT/TTS/chat POSTs always get exactly one attempt.

Conversation prepare/commit separates remote text generation from in-memory history retention.
Voice commits a prepared turn with terminal completion, so cancellation during TTS/playback keeps
no new history. A generation counter prevents clear/shutdown from being undone by an older turn.
Controller start captures its own result/token/release objects; adapters retain session IDs, old
release/cancel events are ignored, wait snapshots its result, and close prevents reactivation.

Capture completion/inactivity and output errors have sanitized codes. Devices are context-managed
per use, not cached. A failed normal session can activate again; a closed controller cannot. An
uncooperative driver/custom adapter may require process restart after bounded shutdown; no attempt
is made to kill a Python thread unsafely. Loopback server shutdown interrupts an active client. Header reads use short cancellable I/O
with a two-second total/64-KiB bound, independent of cross-thread Winsock wakeup behavior; normal
responses retain the two-second socket timeout.

`--health` and `/diagnostics` expose inexpensive configuration/resource snapshots; explicit audio
probe can be added to --health. The existing voice event error_info carries sanitized codes; no
recovery-specific public event types or protocol meaning changes were necessary.

## v0.4 compatibility

Offline preflight declares wire profiles/capabilities separately from live verification. Cloud
adapters preserve the shared transport/permission boundary, with explicit text/JSON transcription,
omission of unsupported optional audio fields, and system/developer/none chat instruction roles.
No SDK, configuration file or live-probe side effect was introduced. See PROVIDERS.md for evidence.

Device adapters query inventory and validate rate/channel/PCM settings before each activation,
retaining explicit identity bindings. Bounded PCM conversion handles output mismatches; optional
native imports remain lazy. A small managed-stream wrapper closes partially started/stopped native
streams even when context initialization fails. No driver refresh service/private reinitialization.

The test-only TLS harness lives under scripts, outside the runtime package. It exercises actual
HTTP STT/chat/TTS in pytest and from an extracted executable. Runtime --mock-audio simulates device
ports only; it still requires explicit activation and configured providers. --mock-voice stays fully
offline. Extracted Windows checks remove development environment bindings and restrict PATH to
Windows system directories. The fixture CA is test input, not a packaged credential or TLS bypass.

v0.5 adds optional `validation` stages selected before ordinary provider startup. Consent gates
precede effects; native streams, cloud transport and PTT reuse existing modules. There is no new
server/endpoint/schema, background task, HTTP client or device monitor. A finite explicit benchmark
uses a fresh credential-free mock child and existing OS resource snapshots.
