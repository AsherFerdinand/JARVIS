# v0.2 portable builds

No user-side Windows installation or testing is requested in this milestone.
Windows CI remains the required platform packaging/compatibility gate; Linux mocks do not
replace it. The workflow uploads these after successful checks:

- JARVIS-0.2.0-windows.zip
- JARVIS-0.2.0-windows.zip.sha256
- artifact-metrics.json (compressed/extracted byte counts; optional measured baseline delta)

The tag v0.2.0 or manual release-candidate workflow reuses the Windows build. No automatic merge
or GitHub Release publication occurs. Download only from a trusted successful Actions run.

CI installs Python 3.12, frozen dependencies with the audio extra/packaging group, runs all tests
and dependency audit, builds PyInstaller onedir, checks frozen text/native-system-info/mock-voice
startup, loads its audio backend without opening streams, and checks the PortAudio DLL exists.
It bundles quick-start, VERSION and an informational default JSON (not a configuration loader).
SHA256SUMS covers every bundle file; archive CRC, complete manifest and each archived SHA256
are verified before upload. The accompanying .sha256 covers the entire ZIP. Models and developer
utilities/tests are not intentionally bundled. Self-contained runtime needs no user Python install.

Artifact size differences are measured only when JARVIS_BASELINE_ZIP_BYTES is supplied with a
real previous Windows ZIP size; otherwise the delta is null. No Windows v0.1 baseline is known.
Unsigned executables remain a distribution trust risk. Actual Windows build status, artifact
availability and measured sizes are recorded in PROGRESS.md; pipeline definitions are not results.

## Future hardware checkpoint (not requested now)

When Windows CI/artifacts and a subsequent validation phase are ready, verify the archive hash
with `Get-FileHash -Algorithm SHA256`, extract, and check --version, --mock --command status,
--mock-voice 'Open YouTube.' --diagnostics, then explicit allowlisted GUI actions. Later consented
voice checks must cover real input/output device selection, press/release limits, overflow/device
loss, cancellation at every phase, English/German accuracy and cloud provider compatibility.
Never claim these are proven by backend load or mocked tests. See VOICE.md and PERFORMANCE.md.
