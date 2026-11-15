# Decisions

- Python 3.12 with standard-library runtime: lowest initial dependency/packaging cost; tools only
  in development groups. Dataclasses suffice; Pydantic and FastAPI add no current value.
- Native Codex repository instructions plus roadmap/progress replace orchestration services.
- Typed intents, allowlisted names and separate Windows executor prevent AI-to-shell execution.
- HTTPS-only optional OpenAI-compatible provider, fixed configured endpoint, no redirects,
  bounded input/output and request timeout. Model and credential are never hardcoded.
- Read-only HTTP snapshot protocol replaces WebSockets initially. Optional one server thread,
  bounded history; no requirement for push delivery yet. Deferred streaming requires a new decision.
- No resource manager: blocking CLI, bounded history and opt-in services give measurable controls
  without a scheduler. No speech implementation until checkpoint B budgets are evaluated.
- PyInstaller onedir portable ZIP avoids onefile extraction startup cost. Suitability is provisional
  until Windows CI builds/smokes it. No installer, signing, or automatic release publication yet.
- Status is session process tracking only; arbitrary process inspection and shell execution excluded.
- v0.1 has no sensitive action capability; a future confirmation mechanism must precede adding one.

## v0.2

- Standard-library OpenAI REST audio formats (verified against published schema) avoid SDK cost;
  full URLs/models/credentials are explicit. JSON transcription and WAV synthesis permit small,
  deterministic contract tests. English/German are explicit language choices; TTS language follows
  text because the API has no language field. No unvalidated live API behavior is claimed.
- Optional sounddevice 0.5.3 raw streams + CFFI avoid numpy/audio frameworks, allow cancellable
  chunks and Windows bundled PortAudio. It is an audio extra, never a core startup import.
- Configurable in-app activation is the supported alternative to a global hotkey. A testable
  press/release/cancel adapter exists; global hooks require later consent and Windows validation.
- One bounded session worker and cooperative cancellation avoid unbounded abandoned request
  threads. Session remains busy until blocked network work drains; action commit is atomic with
  cancellation. Closing the CLI can leave a cancelled daemon request draining until process exit.
- Conversation is text-only with six-turn/16k-character in-memory retention; it cannot execute
  model output. Exact command aliases precede AI; ambiguity never uses fuzzy action matching.
- Keep protocol version 1 with a separate extended snapshot path. Legacy path filters extensions
  for consumers that validate exact v0.1 types/fields. Transcript sharing is a separate opt-in.
- Packaging includes the audio extra, a hidden-import for its lazy module, a PortAudio DLL check,
  backend-load and mock-voice executable smokes. Record size deltas only against a supplied
  measured Windows baseline; no baseline means null rather than a guessed size increase.
