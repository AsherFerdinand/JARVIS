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
Windows CI now records executable compressed/extracted sizes in the artifact metrics; exact
metric retrieval in this session and representative Windows hardware resource targets remain unverified.
The packaging workflow writes artifact-metrics.json rather than guessing a baseline delta.

Linux-only v0.2 frozen validation archive: 15,007,374 compressed bytes; 42,299,602 extracted
logical bytes. Not a Windows artifact or a Windows size baseline.

## v0.3 profiling and shared-runner evidence

Before changes, this host reproduced v0.2's 121 passing tests. Baseline router median/p99 were
0.003735/0.007471 ms; constructor 0.277368 ms; synthetic audio allocation peak 3,891,929 bytes.
No custom memory manager or new HTTP dependency was justified. Bounded temporary copies remain
for WAV/multipart and IPC; input/output chunks now use memoryviews. Mock effect history, events,
conversation text and worker concurrency have explicit bounds.

After changes, router median/p99 sample: 0.003726/0.009324 ms; constructor 0.223988 ms (imports
excluded). Audio synthetic peak 3,892,001 bytes, reflecting bounded copies rather than a claimed
large memory reduction. Import sample: core RSS 17,540 KiB; core+audio 20,760 KiB (3,220 KiB delta).
These separate-process samples are noisy and are not Windows idle/resource acceptance evidence.

`benchmark_reliability.py` warms 128 sessions to fill both bounded histories, then runs 200 more.
Sample: 189.47 ms total, retained traced allocation delta 352 bytes, peak 61,399 bytes, 128 event
and 128 mock-effect entries, zero active request workers afterwards. Initial 10-session warmup
showed about 14 KiB growth while filling the histories, so it was corrected before measuring steady
state. This is a bounded synthetic regression probe, not a long-duration leak or driver test.
Spawn/IPC probes took 92.85–106.17 ms; final helper RSS 18,759,680 bytes, CPU 0.08 seconds, without
network/audio payload. Actual HTTP work adds buffers/TLS/latency; one helper is allowed at a time.
POSIX CPython can retain one resource-tracker helper after spawn; no request child stays alive.

### First Windows v0.3 result (application SHA 4134dfe)

Run: https://github.com/AsherFerdinand/JARVIS/actions/runs/43758145275
Windows Server 2022 10.0.20348, hosted image 20261112.366.7, one finite mock-idle sample:

| Measurement | Result |
| --- | --- |
| Executable readiness | 152.2935 ms (50-ms observation granularity) |
| Sample interval | 5.000632 seconds |
| Process CPU increase | 0.0% measured, one-core and host normalized |
| Working set, before/after | 27,922,432 bytes |
| Private bytes, before/after | 19,755,008 bytes |
| Natural exit | code 0, 3,013.676 ms remaining wait after sampling |
| Separate audio-backend process | 196.186 ms, includes executable startup |
| v0.3 ZIP / extracted | 10,043,980 / 22,619,590 bytes |
| Same-runner v0.2 ZIP / extracted | 9,641,975 / 22,094,697 bytes |
| Change | +402,005 ZIP bytes (4.17%); +524,893 extracted bytes (2.38%) |

The added transport/process/diagnostic code and required standard-library modules are a modest,
explicit size cost; no new mandatory package, model or dataset was added. Baseline and current
use their own locked source in the same runner. Distinct dependency/toolchain changes must not be
silently treated as equivalent baselines in later comparisons. Artifacts contain exact JSON metrics.

CPU uses GetProcessTimes deltas (no measurable increase at its accounting resolution); memory uses
GetProcessMemoryInfo. Readiness is observed after startup with a bounded loop; this is not a
cold-cache guarantee. Natural exit wait includes the remainder of the eight-second probe and is
NOT a three-second shutdown latency. Shared runner load and a five-second sample cannot establish
representative Windows laptop targets. No live devices, paid providers or Windows GUI action was
measured. Later CI adds separately timed native backend initialization and maintained action pins;
see PROGRESS.md for the final verified SHA/result, and retain the hardware checkpoint requirement.
