"""Build a portable Windows bundle; invoked only on Windows CI."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

from validate_portable import validate


def verify_archive(archive: Path) -> None:
    with zipfile.ZipFile(archive) as packaged:
        if packaged.testzip() is not None or "JARVIS/JARVIS.exe" not in packaged.namelist():
            raise ValueError("Invalid portable artifact")
        records = packaged.read("JARVIS/SHA256SUMS").decode().splitlines()
        expected = set()
        for record in records:
            digest, name = record.split("  ", 1)
            member = f"JARVIS/{name}"
            if member in expected or hashlib.sha256(packaged.read(member)).hexdigest() != digest:
                raise ValueError("Portable checksum mismatch")
            expected.add(member)
        if expected | {"JARVIS/SHA256SUMS"} != set(packaged.namelist()):
            raise ValueError("Portable manifest is incomplete")


def main() -> None:
    if os.name != "nt":
        raise SystemExit("Windows packaging requires Windows")
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--hidden-import",
            "sounddevice",
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
    mock = subprocess.run(
        [str(bundle / "JARVIS.exe"), "--mock-voice", "Open YouTube.", "--diagnostics"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if "Website opened (mock)" not in mock.stdout or '"state": "completed"' not in mock.stdout:
        raise RuntimeError("Packaged voice smoke failed")
    subprocess.run([str(bundle / "JARVIS.exe"), "--check-audio-backend"], check=True, timeout=30)
    subprocess.run([str(bundle / "JARVIS.exe"), "--check-provider-worker"], check=True, timeout=15)
    subprocess.run([str(bundle / "JARVIS.exe"), "--health"], check=True, timeout=15)
    portaudio = list(bundle.rglob("libportaudio*.dll"))
    if not portaudio:
        raise RuntimeError("Required Windows PortAudio runtime missing")
    shutil.copy(root / "docs/RELEASES.md", bundle / "QUICKSTART.md")
    (bundle / "VERSION").write_text(f"{version}\n")
    # No informational template masquerades as active configuration. Environment settings only.
    files = sorted(p for p in bundle.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (bundle / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(bundle).as_posix()}\n"
            for p in files
        )
    )
    archive = root / f"dist/JARVIS-{version}-windows.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                output.write(path, path.relative_to(bundle.parent))
    verify_archive(archive)
    validation = validate(archive)
    (root / "dist/portable-validation.json").write_text(json.dumps(validation, indent=2))
    if os.getenv("GITHUB_ACTIONS") == "true":
        print(
            "::notice title=Extracted portable validation::"
            + json.dumps(validation).replace("%", "%25")
        )
    extracted_bytes = sum(p.stat().st_size for p in bundle.rglob("*") if p.is_file())
    print(f"Extracted bytes: {extracted_bytes}")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n")
    baseline = os.getenv("JARVIS_BASELINE_ZIP_BYTES")
    previous = int(baseline) if baseline is not None else None
    metrics = {
        "version": version,
        "zip_bytes": archive.stat().st_size,
        "extracted_bytes": extracted_bytes,
        "baseline_zip_bytes": previous,
        "delta_zip_bytes": archive.stat().st_size - previous if previous is not None else None,
    }
    (root / "dist/artifact-metrics.json").write_text(json.dumps(metrics, indent=2))
    baseline_path = root / "dist/baseline-artifact-metrics.json"
    if baseline_path.exists():
        old = json.loads(baseline_path.read_text())
        metrics["baseline_version"] = old["version"]
        metrics["baseline_zip_bytes"] = old["zip_bytes"]
        metrics["baseline_extracted_bytes"] = old["extracted_bytes"]
        metrics["delta_zip_bytes"] = archive.stat().st_size - old["zip_bytes"]
        metrics["delta_extracted_bytes"] = extracted_bytes - old["extracted_bytes"]
        (root / "dist/artifact-metrics.json").write_text(json.dumps(metrics, indent=2))
    if os.getenv("GITHUB_ACTIONS") == "true":
        print(
            "::notice title=Portable artifact metrics::" + json.dumps(metrics).replace("%", "%25")
        )
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write(
                "### Portable artifact metrics\n\n```json\n"
                + json.dumps(metrics, indent=2)
                + "\n```\n"
            )
    print(f"ZIP bytes: {archive.stat().st_size}; SHA256: {digest}")


if __name__ == "__main__":
    main()
