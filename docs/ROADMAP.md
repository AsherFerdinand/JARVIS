# Roadmap

- v0.1: foundation preserved; approved actions, typed boundaries, text lifecycle and protocol.
- v0.2: voice/AI foundation preserved; 121 Linux checks were the starting baseline. The branch
  was not merged into main when v0.3 began; v0.3 branches from exact v0.2 commit 595db1e.
- v0.3 (active): bounded HTTP lifetime/cancellation/retries, staged history, device/session/shutdown
  recovery, sanitized health, bounded mock-effect records, maintained CI actions, same-runner
  Windows package comparison and finite executable resource measurements. See PROGRESS.md
  for actual validation and exact CI SHAs; pipeline code alone is not proof of success.
- Next: v0.4 should resolve any CI/package/resource findings and prepare a deliberately scoped
  compatibility checkpoint. Live provider and physical device gaps remain explicitly unvalidated.
- Deferred: wake word, continuous recording, global hooks, startup persistence, ORBIT UI work,
  arbitrary shell/computer control and local model bundling require separately assigned scope.

No user-side Windows testing/installation is requested during v0.3. Shared runner CPU/RAM/startup
numbers do not establish laptop acceptance targets. Future hardware checkpoints need automated
checks, an available Windows artifact and a clear separately requested verification guide.
