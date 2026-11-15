"""Bounded shared-runner executable measurements, not laptop acceptance evidence."""

import json
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path

from jarvis.diagnostics.resources import process_resources


def measure(executable: Path) -> dict[str, object]:
    if os.name != "nt":
        raise RuntimeError("Windows executable measurement requires Windows")
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as output:
        started = time.perf_counter()
        process = subprocess.Popen(  # noqa: S603 -- measured executable from own build
            [str(executable), "--mock", "--idle-probe", "8"],
            stdout=output,
            stderr=output,
        )
        try:
            while time.perf_counter() - started < 15:
                output.seek(0)
                if "JARVIS ready" in output.read():
                    break
                if process.poll() is not None:
                    raise RuntimeError("Idle probe exited before readiness")
                time.sleep(0.05)
            else:
                raise TimeoutError("Executable readiness deadline")
            startup = (time.perf_counter() - started) * 1000
            before = process_resources(process.pid)
            sampled = time.perf_counter()
            time.sleep(5)
            after = process_resources(process.pid)
            duration = time.perf_counter() - sampled
            if before["cpu_seconds"] is None or after["cpu_seconds"] is None:
                raise RuntimeError("CPU sampling unavailable")
            cpu = (after["cpu_seconds"] - before["cpu_seconds"]) / duration * 100
            shutdown = time.perf_counter()
            code = process.wait(timeout=5)
            if code != 0:
                raise RuntimeError("Probe did not exit cleanly")
            exit_wait = (time.perf_counter() - shutdown) * 1000
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
    audio_start = time.perf_counter()
    backend = subprocess.run(  # noqa: S603 -- fixed executable from our build
        [str(executable), "--check-audio-backend", "--diagnostics"],
        check=True,
        timeout=15,
        capture_output=True,
        text=True,
    )  # noqa: S603
    backend_process = (time.perf_counter() - audio_start) * 1000
    return {
        "os": platform.platform(),
        "runner": os.getenv("RUNNER_OS", "Windows"),
        "runner_image": os.getenv("ImageVersion", "unknown"),
        "sample_seconds": duration,
        "startup_ready_ms": startup,
        "idle_cpu_percent_one_core": cpu,
        "idle_cpu_percent_host": cpu / (os.cpu_count() or 1),
        "before": before,
        "after": after,
        "natural_exit_wait_ms": exit_wait,
        "exit_code": code,
        "audio_backend_process_ms": backend_process,
        "audio_backend_init_ms": json.loads(backend.stdout.splitlines()[-1])[
            "audio_backend_init_ms"
        ],
        "method": "50ms readiness; process CPU/memory APIs before/after 5s idle; "
        "8s finite idle probe, clean natural exit; audio import in separate process",
        "limitations": "shared hosted runner; single sample, core mock idle, no audio streams; "
        "audio process time includes interpreter/bootloader startup",
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    report = measure(root / "dist/JARVIS/JARVIS.exe")
    payload = json.dumps(report, indent=2)
    (root / "dist/windows-resources.json").write_text(payload)
    print(payload)
    if os.getenv("GITHUB_ACTIONS") == "true":
        print("::notice title=Windows resource metrics::" + json.dumps(report).replace("%", "%25"))
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as output:
            output.write("### Shared Windows runner resources\n\n```json\n" + payload + "\n```\n")


if __name__ == "__main__":
    main()
