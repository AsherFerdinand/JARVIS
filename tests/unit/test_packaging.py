import hashlib
import runpy
import zipfile
from pathlib import Path

import pytest


def test_portable_checksum_verifier_detects_corruption(tmp_path):
    verify = runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "scripts/package_windows.py")
    )["verify_archive"]
    for content, succeeds in [(b"executable", True), (b"corrupt", False)]:
        archive = tmp_path / "portable.zip"
        manifest = hashlib.sha256(b"executable").hexdigest() + "  JARVIS.exe\n"
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("JARVIS/JARVIS.exe", content)
            output.writestr("JARVIS/SHA256SUMS", manifest)
        if succeeds:
            verify(archive)
        else:
            with pytest.raises(ValueError, match="checksum"):
                verify(archive)
