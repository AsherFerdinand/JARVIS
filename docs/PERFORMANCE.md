# v0.5 performance checkpoint

Optional `--validation-benchmark` measures finite mock idle CPU/working set/private memory and
fresh readiness without audio/network. See VALIDATION.md for reproducible commands, sample
limits and explicit scope labels. Fresh startup is not verified cold-cache startup. Capture/
playback report local activation and elapsed times. Cloud requests report aggregate wall times
including worker startup/TLS/network/provider; these cannot isolate pure network or remote compute.
Linux sample: routing median .003736ms / p99 .016975ms (10,000 routes), core construction
.2073ms (not process startup), 20 mock sessions 18.82ms; reliability 200 sessions after warmup
retained +352 bytes, peak traced 63,359 bytes, zero request workers. These are synthetic cloud
measurements, not Windows/laptop acceptance. No new dependency, model, monitor or background service was added. Same-runner comparison uses
exact v0.4 ff09385, including extracted ZIP resource measurements. Existing provisional targets
remain unchanged; cloud/CI samples do not establish representative laptop acceptance.

## v0.5 same-runner Windows result

Tested e71d4ad; Windows CI run 43922424596 passed all tests and extracted/package checks.
Exact v0.4 ff09385 was archived and rebuilt on the same runner, preserving tracked history.

| Metric | v0.4 rebuilt | v0.5 | Interpretation |
| --- | ---: | ---: | --- |
| ZIP bytes | 10,059,608 | 10,077,752 | +18,144 (+0.1804%) |
| Extracted bytes | 22,636,271 | 22,654,647 | +18,376 (+0.0812%) |
| Working set bytes | 28,147,712 | 28,098,560 | −49,152; sample noise |
| Private bytes | 19,898,368 | 19,824,640 | −73,728; sample noise |
| Idle CPU, one core | 0% measured increase | 0% measured increase | finite ~5s; API resolution applies |
| Ready ms | 326.591 | 328.015 | 50ms polling; fresh, not verified cold |
| Native backend init ms | 43.003 | 42.508 | no audio stream |

Windows Server 2022 image 20261112.366.7; both finite mock-idle probes exited naturally with code0.
No material regression appeared. This is one hosted sample, no actual mic/speaker/provider/laptop
measurement. Compression metadata can vary between builds; use same-runner numbers above.
New extracted validation benchmark and local TLS stage checks also passed; their full sanitized
reports are in portable-validation.json. Request walls include worker/TLS/remote work, not isolated
network latency. No claim is made that audibility or language accuracy passed.

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

### Verified Windows v0.3 result (application SHA 27fdb80)

Run: https://github.com/AsherFerdinand/JARVIS/actions/runs/43759843983
Windows Server 2022 10.0.20348, hosted image 20261112.366.7; all 160 tests passed. One finite
mock-idle executable sample, with native backend initialization measured separately:

| Measurement | Result |
| --- | --- |
| Executable readiness | 152.001 ms (50-ms observation granularity) |
| Sample interval | 5.000401 seconds |
| Process CPU increase | 0.0% measured, one-core and host normalized |
| Working set, before/after | 27,770,880 bytes |
| Private bytes, before/after | 19,890,176 bytes |
| Natural exit | code 0; 2,996.038 ms remaining wait after sampling |
| Native audio-backend initialization | 34.836 ms, excluding process startup |
| Separate audio-backend process | 169.790 ms, including executable startup |
| v0.3 ZIP / extracted | 10,045,150 / 22,620,450 bytes |
| Same-runner v0.2 ZIP / extracted | 9,641,990 / 22,094,697 bytes |
| Change | +403,160 ZIP bytes (4.18%); +525,753 extracted bytes (2.38%) |

The added transport/process/diagnostic code and required standard-library modules are a modest,
explicit size cost; no new mandatory package, model or dataset was added. Baseline and current
use their own locked source in the same runner. Baseline ZIP compression/timestamps may vary
slightly across runs; the extracted baseline was unchanged. Distinct dependency/toolchain changes
must not be silently treated as equivalent baselines later. Artifacts contain exact JSON metrics.

CPU uses GetProcessTimes deltas (no measurable increase at its accounting resolution); memory uses
GetProcessMemoryInfo. Readiness is observed after startup with a bounded loop; this is not a
cold-cache guarantee. Natural exit wait includes the remainder of the eight-second probe and is
NOT a three-second shutdown latency. Shared runner load and a five-second sample cannot establish
representative Windows laptop targets. No live devices, paid providers or Windows GUI actions
were measured. Native init opens no stream; it does not establish an audible speaker or working
microphone. Preserve the separately scoped hardware checkpoint requirement.

## v0.4 compatibility profile (2026-11-16)

Linux sample: router median/p99 0.003746/0.009184 ms, constructor 0.165726 ms (imports excluded).
128 warmup + 200 synthetic sessions: 186.456 ms total, 408 retained traced bytes, peak 62,855,
128 event/effect entries and zero surviving request workers. v0.3's sample was 352 retained bytes
and 61,399 peak; these tiny differences are fixed instrumentation/allocation variation, not evidence
of a growing queue or a long-duration leak result. Probe startup 81.29–97.20 ms, helper RSS
18,927,616 bytes; these are synthetic spawn costs, not network or hardware latency.

Audio benchmark traced peak 3,891,993 bytes versus v0.3's 3,892,001 (essentially unchanged); max
fixture 1,920,044 bytes. Core/audio-import Linux RSS 17,532/20,776 KiB (3,244 KiB delta), compared
with previous 17,540/20,760. No idle/background/device polling or mandatory runtime dependency was
added. PCM conversion activates only on format mismatch and checks size/duration/cancellation;
its actual device latency/quality has not been measured on hardware.

### Verified extracted Windows v0.4 result (16635ba)

https://github.com/AsherFerdinand/JARVIS/actions/runs/43872875094 — Server 2022 10.0.20348,
image 20261112.366.7, actual extracted executables, five-second mock idle, same-runner baseline:

| Metric | v0.4 | Rebuilt v0.3 |
| --- | --- | --- |
| Readiness ms (50-ms observation granularity) | 383.014 | 387.768 |
| Native backend init ms, excluding startup | 48.375 | 49.619 |
| Working set bytes | 28,086,272 | 27,893,760 |
| Private bytes | 19,955,712 | 19,939,328 |
| Measured idle CPU increase | 0.0% | 0.0% |
| Application ZIP bytes | 10,060,538 | 10,044,701 |
| Extracted logical bytes | 22,636,271 | 22,620,450 |

The ZIP/extracted delta is +15,837/+15,821 bytes (about 0.16%/0.07%); working set +192,512,
private +16,384 bytes. No material package/memory regression was observed in this sample. New
validation/conversion code remains small, with no new mandatory dependency or model. Startup
is not a claimed optimization: shared runner load/caches/sampling/baseline ordering vary. Windows
laptop CPU/RAM/startup targets remain unverified. CPU accounting saw no change at its resolution;
a short sample does not establish literal zero CPU use. Exit code 0 is a clean natural exit; the
remaining three-second wait is the rest of the eight-second probe, not shutdown latency.

Extracted mock voice: 21,001 traced peak bytes, 28,127,232 peak working-set bytes. Real local HTTP
paths in the extracted executable: 4,018,346 traced peak bytes and about 32.2 MB peak working set,
including instrumented transient request buffers. Both cases returned request workers to zero.
These single-session peaks are not directly comparable to the 20-session/max-fixture Python
benchmark above. Their input/output devices were simulated; native enumeration found zero devices
and opened zero streams. No real microphone/speaker, USB/Bluetooth, paid-provider/model latency
or audio-conversion quality was measured. Exact resources/portable/baseline JSON is published
with the artifact and sanitized notices. CI passed 203 tests; see PROGRESS.md for source and links.
