# Decisions

- Python 3.12 with standard-library runtime: lowest initial dependency/packaging cost; tools only
  in development groups. Dataclasses suffice; Pydantic and FastAPI add no current value.
- Native Codex repository instructions plus roadmap/progress replace orchestration services.
- Typed intents, allowlisted names and separate Windows executor prevent AI-to-shell execution.
- HTTPS-only optional OpenAI-compatible provider, fixed configured endpoint, no redirects,
  bounded input/output and request timeout. Model and credential are never hardcoded.
- Read-only HTTP snapshot protocol replaces WebSockets initially. Optional one server thread,
  bounded history; no requirement for push delivery yet. Deferred streaming requires a new decision.
- No resource manager: blocking CLI, bounded history and opt-in services give measurable controls
  without a scheduler. No speech implementation until checkpoint B budgets are evaluated.
- PyInstaller onedir portable ZIP avoids onefile extraction startup cost. Suitability is provisional
  until Windows CI builds/smokes it. No installer, signing, or automatic release publication yet.
- Status is session process tracking only; arbitrary process inspection and shell execution excluded.
- v0.1 has no sensitive action capability; a future confirmation mechanism must precede adding one.

## v0.2

- Standard-library OpenAI REST audio formats (verified against published schema) avoid SDK cost;
  full URLs/models/credentials are explicit. JSON transcription and WAV synthesis permit small,
  deterministic contract tests. English/German are explicit language choices; TTS language follows
  text because the API has no language field. No unvalidated live API behavior is claimed.
- Optional sounddevice 0.5.3 raw streams + CFFI avoid numpy/audio frameworks, allow cancellable
  chunks and Windows bundled PortAudio. It is an audio extra, never a core startup import.
- Configurable in-app activation is the supported alternative to a global hotkey. A testable
  press/release/cancel adapter exists; global hooks require later consent and Windows validation.
- One bounded session worker and cooperative cancellation avoid unbounded abandoned request
  threads. Session remains busy until blocked network work drains; action commit is atomic with
  cancellation. Closing the CLI can leave a cancelled daemon request draining until process exit.
- Conversation is text-only with six-turn/16k-character in-memory retention; it cannot execute
  model output. Exact command aliases precede AI; ambiguity never uses fuzzy action matching.
- Keep protocol version 1 with a separate extended snapshot path. Legacy path filters extensions
  for consumers that validate exact v0.1 types/fields. Transcript sharing is a separate opt-in.
- Packaging includes the audio extra, a hidden-import for its lazy module, a PortAudio DLL check,
  backend-load and mock-voice executable smokes. Record size deltas only against a supplied
  measured Windows baseline; no baseline means null rather than a guessed size increase.

## v0.3 reliability

- Profiling began from v0.2: 121 tests passed; router median 0.003735 ms/p99 0.007471 ms;
  synthetic voice allocation peak 3,891,929 bytes. No evidence justified a memory manager or
  an HTTP SDK. Standard-library urllib remains the wire implementation.
- Each real HTTP attempt runs in a spawn child with a parent monotonic deadline. This bounds
  DNS, TLS, headers and slow-drip bodies even when urllib's socket timeout cannot. Cancellation
  terminates/reaps that local process; it does not cancel/undo a remote charge or operation.
  This trades temporary startup/RAM/IPC-copy cost for bounded request lifetime, without another
  runtime dependency. One global request slot prevents concurrent worker accumulation. POSIX
  CPython can retain its one resource-tracker helper; Windows uses native spawn handles.
- Connection timeout defaults 10 seconds (capped by response timeout), response inactivity 15,
  total deadline 30; all configurable, >0 and <=120. Queue wait/process startup count toward the
  total; OS process cleanup allows up to 0.5 seconds beyond it. Response cap 64 KiB JSON / 4 MB
  WAV; request cap 4,010,000 bytes. TLS and redirect restrictions remain enabled.
- POST retries are forbidden because lost responses can still incur remote work/charges. Only
  explicit GET/HEAD requests retry transient network/timeouts/429/5xx, at most 3 attempts under
  one deadline, exponential 0.2-second base, <=2-second backoff and <=0.1-second positive jitter.
  Numeric Retry-After is honored within the delay cap; larger values stop automatic retries.
- A cancellation request no longer waits for the action lock. A successful check at the commit
  gate is the irreversible-operation linearization point; previously committed actions may finish.
  Voice history is staged and retained only at successful session completion. Clear invalidates
  older prepared turns. Shutdown closes the controller permanently and joins for <=2 seconds;
  a non-cooperative custom/native adapter cannot spawn replacement workers through it.
- Capture uses finished callbacks plus 50-ms activity checks only while activated. Stream failure
  releases context managers; the next session opens a fresh device/default selection. Input/output
  chunks use memoryviews to avoid extra full-chunk copies. No silent continuous-recording fallback.
- Event server closes an active client socket before shutdown so partial/slow headers cannot
  hold shutdown open. Auth, paths, ordering and legacy field filtering remain unchanged.
- Health output reports presence/status, not credentials, endpoint/model/device names or content.
  Native backend probing is explicit; a package being installed is not proof it loads or has devices.
- CI uses immutable Node.js 24 action releases (checkout 6/setup-python 6/upload-artifact 6),
  branch/PR concurrency and tag-only reusable release packaging. A same-runner v0.2 source archive
  build establishes actual package-size deltas without moving/resetting the development checkout.
  Windows measurements are finite mock-idle probes, not representative laptop acceptance tests.
