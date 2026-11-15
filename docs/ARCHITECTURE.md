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

Speech protocols describe replaceable STT/TTS/wake-word/microphone/output boundaries only.
No model selection or implementation is made. Future Ollama support can implement Provider;
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
