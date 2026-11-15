# Performance

Run `uv run python scripts/benchmark.py`. JSON reports 10,000 deterministic routes, median/p99,
core constructor time, and traced Python allocations on the recorded OS. This excludes imports,
interpreter startup, OS launches, network calls, and speech. Tracemalloc adds overhead and is
not process RSS. This does not measure idle CPU, installed size, or Windows hardware latency.

Provisional Windows targets: <1% average idle CPU, <100 MB core RAM without models, <50 ms
routing excluding app startup, <2 seconds core initialization. Establish installed ZIP and
extracted size baselines in Windows CI before imposing limits. No targets claimed met yet.

Checkpoint A: record OS/CPU/RAM, executable cold start, working set/private bytes, and idle CPU
over 60 seconds after settling; repeat runs with no optional services/models. Compare event
server enabled separately. CI is shared/variable hardware; representative laptop remains needed.

## Initial Linux cloud sample (2026-11-15)
10,000 routes: median 0.003349 ms, p99 0.006723 ms, constructor 0.134514 ms.
Traced peak allocations 327,116 bytes, including benchmark samples. Linux onedir PyInstaller
output: du 34,764 KiB. These figures are diagnostic baselines, not Windows resource claims.
