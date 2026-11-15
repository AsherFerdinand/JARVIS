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
