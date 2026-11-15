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

## v0.2 cloud sample (2026-11-15)

`benchmark_voice.py` runs 20 synthetic sessions and a max-size capture allocation; no paid network,
recording, playback stream, hardware latency or audible sound is measured. Sample elapsed 31.51 ms
including fixture allocation; last session 0.584 ms; traced peak 3,891,929 bytes including temporary
copies. Maximum 60-second 16-kHz mono PCM WAV is 1,920,044 bytes. Input/output cap is 4 MB;
HTTP multipart/WAV decoding makes bounded additional copies. History/event/session limits are in VOICE.md.

Separate Linux child-process import sample: core RSS 16,836 KiB, core plus optional sounddevice
20,048 KiB, observed delta 3,212 KiB. Both max-RSS readings were 22,528 KiB (high-water
readings that do not resolve the import delta); current RSS comes from /proc/self/status. One-sample noise/allocator
and OS differences limit these figures. No device stream or idle Windows resource guarantee follows.
Python distribution bytes: sounddevice 128,555; cffi 735,705; pycparser 262,288, excluding Linux
system PortAudio. This cloud host initially lacked PortAudio; a signature/checksum-verified Debian
libportaudio2 package was extracted locally for import/frozen validation. Default mocks do not need it.
For this host only: set LD_LIBRARY_PATH to .cache/native/usr/lib/x86_64-linux-gnu before import
benchmarks; fresh environments can use their distribution's trusted PortAudio package instead.

Portable router sample: median 0.003883 ms, p99 0.008116 ms; constructor 0.123518 ms.
Windows executable compressed/extracted sizes and resource targets remain pending Windows CI.
The packaging workflow writes artifact-metrics.json rather than guessing a baseline delta.

Linux-only v0.2 frozen validation archive: 15,007,374 compressed bytes; 42,299,602 extracted
logical bytes. Not a Windows artifact or a Windows size baseline.
