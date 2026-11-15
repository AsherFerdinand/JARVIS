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
