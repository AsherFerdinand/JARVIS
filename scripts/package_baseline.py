"""Build the exact v0.3 source in an ignored archive directory on the same Windows runner."""

import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

BASELINE = "07d7e56960d8df55122c451a2444542448a541ae"


def main() -> None:
    if os.name != "nt":
        raise SystemExit("Windows baseline requires Windows")
    root = Path(__file__).resolve().parents[1]
    archive = root / ".cache/v03-source.tar"
    baseline = root / ".cache/baseline-v03"
    archive.parent.mkdir(parents=True, exist_ok=True)
    # Only generated files below .cache are replaced; no tracked checkout/worktree is changed.
    if baseline.exists():
        shutil.rmtree(baseline)
    baseline.mkdir()
    with archive.open("wb") as output:
        subprocess.run(["git", "archive", BASELINE], cwd=root, stdout=output, check=True)  # noqa: S603,S607
    with tarfile.open(archive) as source:
        source.extractall(baseline, filter="data")
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv missing")
    subprocess.run(  # noqa: S603 -- resolved uv tool, fixed build arguments
        [
            uv,
            "run",
            "--locked",
            "--extra",
            "audio",
            "--group",
            "packaging",
            "python",
            "scripts/package_windows.py",
        ],
        cwd=baseline,
        check=True,
        timeout=180,
    )  # noqa: S603
    metrics = json.loads((baseline / "dist/artifact-metrics.json").read_text())
    metrics["source_revision"] = BASELINE
    (root / "dist").mkdir(exist_ok=True)
    (root / "dist/baseline-artifact-metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
