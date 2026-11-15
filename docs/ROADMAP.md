# Roadmap

- Phase 0: architecture, agent continuity, locked Python tooling, CI/security/performance conventions.
- v0.1: text lifecycle, approved routing, Windows/mock effects, optional AI interface, bounded events,
  authenticated loopback snapshots, tests, benchmark, Windows portable artifact pipeline.
- Checkpoint A (next): run Windows CI, inspect ZIP/smoke results, measure representative hardware
  startup/RAM/idle CPU and approve safe GUI launches. No local test request before artifact exists.
- Checkpoint B: evaluate speech cost; optional microphone/STT/TTS with no default capture.
- Checkpoint C: optional wake word, background operation and startup behavior.
- Checkpoint D: integrate actual ORBIT UI; reconnect and end-to-end voice tests.

Each checkpoint requires automated checks, Windows ZIP/checksums, exact manual guide and artifact
availability before requesting hardware validation. No ORBIT modifications in the foundation.
