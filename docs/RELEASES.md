# Windows checkpoint A verification

Windows build workflow uploads JARVIS-0.1.0-windows ZIP and .sha256 to Actions artifacts.
Tag/manual release-candidate workflow reuses it; it does not publish a GitHub Release.
No artifact exists until Windows CI succeeds. Download artifacts only from a trusted run.

```powershell
Get-FileHash .\JARVIS-0.1.0-windows.zip -Algorithm SHA256
# Compare with the accompanying .zip.sha256 before extraction.
Expand-Archive .\JARVIS-0.1.0-windows.zip -DestinationPath .\jarvis-portable
cd .\jarvis-portable\JARVIS
.\JARVIS.exe --version
.\JARVIS.exe --mock --command status
.\JARVIS.exe --command 'system info'
.\JARVIS.exe
```

When checkpoint A artifact/CI is available: in interactive mode try status, open notepad,
status notepad, open youtube, exit. Confirm only approved targets open, exit leaves user apps
open, no microphone indicator, and no network listener by default. Record startup and idle
resource baseline per PERFORMANCE.md. The JSON default-config file is informational, not loaded;
defaults are compiled into the application, with optional provider/token environment settings.

Unsigned portable builds may trigger Windows warnings. Signing/distribution trust and Windows
hardware measurements remain release risks. No user-side install required for intermediate work.
