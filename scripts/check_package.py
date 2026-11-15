"""Verify built wheel records, runtime dependency policy, and sdist contents."""

import base64
import csv
import hashlib
import io
import tarfile
import zipfile
from pathlib import Path


def main() -> None:
    dist = Path(__file__).resolve().parents[1] / "dist"
    with zipfile.ZipFile(dist / "jarvis_assistant-0.1.0-py3-none-any.whl") as wheel:
        if wheel.testzip() is not None:
            raise ValueError("Corrupt wheel")
        metadata = wheel.read("jarvis_assistant-0.1.0.dist-info/METADATA").decode()
        if "Requires-Dist:" in metadata:
            raise ValueError("Unexpected runtime dependency")
        record_name = "jarvis_assistant-0.1.0.dist-info/RECORD"
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
    with tarfile.open(dist / "jarvis_assistant-0.1.0.tar.gz") as source:
        names = source.getnames()
        if any(
            part.startswith((".cache", ".venv", ".env"))
            for name in names
            for part in Path(name).parts
        ):
            raise ValueError("Local configuration leaked into sdist")
        if not any(name.endswith("src/jarvis/main.py") for name in names):
            raise ValueError("Application missing from sdist")
    print("Wheel RECORD, zero runtime dependencies, and source distribution verified")


if __name__ == "__main__":
    main()
