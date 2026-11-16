# JARVIS v0.5 portable build and configuration reference

No local Windows installation or testing is requested for this milestone. CI produces
JARVIS-0.5.0-windows.zip and .zip.sha256 plus artifact/baseline/resource/portable-validation JSON.
The ZIP contains its runtime, VERSION, QUICKSTART and a complete SHA256SUMS manifest. No local
Python/development environment, model, test key/data or cache is required/bundled. Executables
remain unsigned; download only from a trusted successful run and verify the accompanying hash.

## Configuration and safe modes

These document operation, not a request to perform a hardware test now:

- `JARVIS.exe --mock-voice "Open YouTube." --diagnostics`: fully offline synthetic voice/OS pipeline.
- `JARVIS.exe --provider-preflight`: offline provider syntax/capability report; no API calls.
- `JARVIS.exe --health`: sanitized status. `--check-audio-backend`: load PortAudio, no streams.
- `JARVIS.exe --list-audio-devices`: explicitly enumerate. `--audio-preflight`: test formats without recording.
- Set JARVIS_STT_URL/MODEL/KEY and JARVIS_TTS_URL/MODEL/KEY/VOICE securely in the environment.
  Optional JARVIS_AI_URL/MODEL/KEY enables conversations. No model is chosen automatically.
- Full HTTPS bearer endpoints use transcription multipart JSON/text, TTS WAV PCM16 and
  non-streamed chat-completions text. JARVIS_VOICE_LANGUAGE=en/de; JARVIS_TTS_RATE=0.25–4.
  Profiles/overrides are documented at docs/PROVIDERS.md in the repository; not every compatible
  endpoint/model/voice supports identical fields. Local validation is never live verification.
- JARVIS_INPUT_DEVICE/OUTPUT_DEVICE select a unique name or index:N; absent uses the default.
- `JARVIS.exe --voice`: in-app /voice activation, Enter releases, /cancel cancels. --no-speak
  disables TTS/output. --voice-trigger changes the activation command. No global hooks/wake word.
- --voice-file explicitly uploads the chosen bounded WAV. --mock mocks OS effects only;
  --mock-audio mocks devices only and DOES NOT disable configured provider requests/charges.

Configuration is actually consumed from environment variables; no active or informational JSON
configuration template is shipped. Never store keys in source, command arguments or this guide.

## CI evidence and limitations

Windows CI runs tests/audit and baseline/current builds, then verifies ZIP CRC/complete manifest
hashes. Smokes run against a fresh extracted executable outside the checkout, with dev bindings
removed and system-only PATH: version/text/mock voice, health/preflight/backend/worker init,
headless-capable device enumeration, real local TLS STT/action/TTS and STT/chat/TTS, worker cleanup.
The test server/fixture CA remain external test inputs; no physical device or paid endpoint is used.

Finite idle/native-backend/resource probes also use extracted v0.3/current executables on the same
runner. Portable validation records mock voice process/traced peaks and worker counts. Artifacts
and sanitized notices expose measured counts/sizes/CPU/RAM. Shared runner or fake-device success
is not representative laptop, real USB/Bluetooth, microphone/speaker or live API proof. See
PROGRESS.md/PERFORMANCE.md for exact tested SHA, run links, results and remaining gaps.

Tags/manual releases reuse the same least-privilege job; no automatic merge, installer, signing
or GitHub Release publication. A future scoped checkpoint must cover live provider/device behavior.

Optional independent checks: see [controlled validation guide](VALIDATION.md). No live or device check runs at startup.

For tested revision e71d4ad, Windows run 43922424596 produced the SHA256-verified ZIP
(10,077,752 bytes; 22,654,647 extracted). The artifact includes portable-validation.json and
same-runner v0.4 comparisons. See PROGRESS.md for exact results and deferred hardware evidence.
