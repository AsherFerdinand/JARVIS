# v0.3 portable builds

No local Windows installation or testing is required during this milestone. Windows Actions builds
JARVIS-0.3.0-windows.zip and .zip.sha256, with artifact-metrics.json, baseline-artifact-metrics.json
and windows-resources.json. A v0.3.0 tag or manual release workflow calls the same packaging job;
branch/PR concurrency limits duplicate jobs, and tag pushes do not also launch branch packaging.
No merge, installer, signing or GitHub Release publication occurs automatically.

CI installs locked Python 3.12 tooling/audio dependencies, runs tests/audit, archives exact v0.2
source under ignored .cache (without modifying any checkout), and rebuilds that baseline in the
same runner/toolchain. It then builds v0.3 with PyInstaller onedir, verifies text/system-info,
mock voice, isolated worker spawn, health/backend load and PortAudio DLL presence. Complete ZIP
manifest SHA256/CRC checks run before upload. Baseline/current sizes and deltas are reported as
sanitized notices and JSON metrics; Actions wrapper size is not the application ZIP size.

Windows resources use a finite 8-second mock-idle executable, with 5-second CPU/memory sampling,
readiness/deadline checks, natural process exit and a separate backend-import process. The JSON
records OS/runner/method/interval/limits. It is a shared-host sample, not a physical microphone,
speaker, laptop idle or cold-cache benchmark. Private bytes/working set are distinct measurements.

Download only from a trusted successful run. The portable runtime needs no user Python/dev tools
and includes no speech/LLM models, test TLS keys, datasets or cache. The default JSON remains
informational. Executables are unsigned; this remains a distribution-trust limitation. See
PROGRESS.md for actual run links/status/sizes, not assumptions from workflow definitions.
