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
