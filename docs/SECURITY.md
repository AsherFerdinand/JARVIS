# Security and privacy

No credentials committed, logs of commands, conversation persistence, telemetry, microphone,
file/screenshot uploads, shell execution, or destructive actions. Approved names map to fixed
HTTPS websites and Windows System32 Notepad. The registry rejects unapproved AI output.
No confirmation bypass flag exists. Future destructive actions require a separately reviewed,
user-bound confirmation flow. Configuration/environment and installed Windows are trusted.

Network: approved browser navigation sends data to www.youtube.com when requested; optional
AI sends the user's unknown command to the explicitly configured HTTPS endpoint using a bearer
key (JARVIS_AI_KEY). Deterministic commands never use AI. Provider redirects are blocked; errors
shown by CLI are generic to avoid credential leakage. HTTPS verification remains enabled.
AI account and retention policies are the user's provider's responsibility.

Event server is optional, IPv4 localhost only, bearer authenticated, read-only, no CORS,
no token logging, no disk history. Generate a random token of >=32 ASCII characters securely;
never pass tokens on command lines. Local hostile processes can still observe environment or
attack availability. This is not a sandbox against malware under the same Windows account.
Future persistent credentials should use Windows Credential Manager; v0.1 persists none.

CI uses read-only repository permissions and commit-pinned actions. Dependency audit runs in CI.
Unsigned development ZIPs are not a trusted distribution channel; signing remains future work.

## v0.2 explicit audio processing

The earlier no-microphone statement describes defaults: `--voice` plus an in-app activation
is now required for live capture. `--voice-file` is explicit consent to upload that selected WAV.
Configuring credentials alone never starts capture or sends audio. Mock voice never sends data.
Recorded audio and synthesized WAVs remain in bounded memory; no temporary audio files are made.
STT uploads the recording to JARVIS_STT_URL; TTS uploads response text to JARVIS_TTS_URL;
unknown conversational requests/history go to JARVIS_AI_URL. Keys are independent bearer settings,
never source-controlled, logged, included in events, or embedded in URL credentials. Redirects
are denied; HTTPS verification stays enabled. Cloud account retention policies apply.

Transcript and conversation text are transient process memory. ORBIT transcript sharing defaults
Off and requires JARVIS_SHARE_TRANSCRIPT=1 on the authenticated extended channel. Event failures
contain generic error codes, never exception/provider bodies. Fixed-message logs remain opt-in.
Late cancelled responses are discarded; no new worker can overlap one draining a socket. Side
effects committed before cancellation are not reversible. No new sensitive actions or confirmation
bypass was added. Exact STT errors can still misrecognize a safe allowlisted command; no destructive
commands exist. Global keyboard hooks and wake-word capture remain absent.
