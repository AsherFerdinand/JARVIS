# Roadmap

- Phase 0 / v0.1: foundation merged into main; text routing, boundaries, protocol, CI and docs.
- v0.2 (this branch): optional push-to-talk capture, cloud/mock STT/TTS, bounded conversations,
  explicit cancellable sessions, legacy-compatible voice events, tests and portable packaging.
- Validation: Windows CI/ZIP succeeded (see PROGRESS.md). Representative hardware evidence
  for checkpoints A/B remains pending. v0.2 is cloud-only; no local installation/testing requested.
- v0.3 recommendation: harden from Windows CI evidence; validate cancellation/device recovery,
  provider compatibility and resource budgets before considering a consented global shortcut.
  No wake word or ORBIT modification is implicitly authorized by this roadmap.
- Later checkpoint C: optional wake word/background/startup only after model/resource evaluation.
- Later checkpoint D: integrate actual ORBIT UI and end-to-end voice; no ORBIT changes here.

Each future hardware checkpoint needs automated checks, an available Windows ZIP/checksum,
exact manual guide, and an explicit user request for hardware validation at the appropriate phase.
