"""Verify built wheel records, runtime dependency policy, and sdist contents."""

import base64
import csv
import hashlib
import io
import tarfile
import tomllib
import zipfile
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    dist = root / "dist"
    with zipfile.ZipFile(dist / f"jarvis_assistant-{version}-py3-none-any.whl") as wheel:
        if wheel.testzip() is not None:
            raise ValueError("Corrupt wheel")
        metadata = wheel.read(f"jarvis_assistant-{version}.dist-info/METADATA").decode()
        requirements = [line for line in metadata.splitlines() if line.startswith("Requires-Dist:")]
        if any(
            "sounddevice==0.5.3" not in line or "extra == 'audio'" not in line
            for line in requirements
        ):
            raise ValueError("Unexpected mandatory runtime dependency")
        record_name = f"jarvis_assistant-{version}.dist-info/RECORD"
        rows = list(csv.reader(io.StringIO(wheel.read(record_name).decode())))
        if {row[0] for row in rows} != set(wheel.namelist()):
            raise ValueError("Incomplete wheel RECORD")
        for name, checksum, size in rows:
            if name == record_name:
                continue
            payload = wheel.read(name)
            digest = (
                base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode()
            )
            if checksum != f"sha256={digest}" or int(size) != len(payload):
                raise ValueError(f"Invalid wheel entry: {name}")
    with tarfile.open(dist / f"jarvis_assistant-{version}.tar.gz") as source:
        names = source.getnames()
        if any(
            part.startswith((".cache", ".venv", ".env"))
            for name in names
            for part in Path(name).parts
        ):
            raise ValueError("Local configuration leaked into sdist")
        if not any(name.endswith("src/jarvis/main.py") for name in names):
            raise ValueError("Application missing from sdist")
    print("Wheel RECORD, zero mandatory runtime dependencies, and source distribution verified")


if __name__ == "__main__":
    main()
