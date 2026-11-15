"""Build a portable Windows bundle; invoked only on Windows CI."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def main() -> None:
    if os.name != "nt":
        raise SystemExit("Windows packaging requires Windows")
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--name",
            "JARVIS",
            str(root / "src/jarvis/main.py"),
        ],
        cwd=root,
        check=True,
    )
    bundle = root / "dist/JARVIS"
    # Validate the packaged runtime, not the Python source command.
    subprocess.run(
        [str(bundle / "JARVIS.exe"), "--mock", "--command", "status"], check=True, timeout=30
    )
    subprocess.run([str(bundle / "JARVIS.exe"), "--command", "system info"], check=True, timeout=30)
    shutil.copy(root / "docs/RELEASES.md", bundle / "QUICKSTART.md")
    (bundle / "VERSION").write_text("0.1.0\n")
    (bundle / "default-config.json").write_text(
        json.dumps(
            {
                "speech_enabled": False,
                "event_server_enabled": False,
                "note": "Defaults are built in; this file is informational",
            }
        )
    )
    files = sorted(p for p in bundle.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (bundle / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(bundle).as_posix()}\n"
            for p in files
        )
    )
    archive = root / "dist/JARVIS-0.1.0-windows.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                output.write(path, path.relative_to(bundle.parent))
    with zipfile.ZipFile(archive) as packaged:
        if packaged.testzip() is not None or "JARVIS/JARVIS.exe" not in packaged.namelist():
            raise RuntimeError("Invalid portable artifact")
    extracted_bytes = sum(p.stat().st_size for p in bundle.rglob("*") if p.is_file())
    print(f"Extracted bytes: {extracted_bytes}")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n")
    print(f"ZIP bytes: {archive.stat().st_size}; SHA256: {digest}")


if __name__ == "__main__":
    main()
