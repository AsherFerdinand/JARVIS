"""Finite fresh-process snapshot. No devices, credentials or network are needed."""

import os
import subprocess
import sys
import tempfile
import time
from threading import Event

from jarvis.diagnostics.resources import process_resources


def benchmark(seconds: float = 5, scope: str = "unclassified") -> dict[str, object]:
    if not 1 <= seconds <= 10:
        raise ValueError("Benchmark interval must be 1–10 seconds")
    command = [sys.executable]
    if not getattr(sys, "frozen", False):
        command += ["-m", "jarvis.main"]
    command += ["--mock", "--idle-probe", str(seconds + 2)]
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("JARVIS_") and key not in {"PYTHONHOME", "PYTHONPATH"}
    }
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as output:
        started = time.perf_counter()
        process = subprocess.Popen(command, stdout=output, stderr=output, env=environment)  # noqa: S603
        try:
            while time.perf_counter() - started < 15:
                output.seek(0)
                if "JARVIS ready" in output.read():
                    break
                if process.poll() is not None:
                    raise RuntimeError("Probe failed before readiness")
                Event().wait(0.05)
            else:
                raise TimeoutError("Probe readiness deadline")
            startup = (time.perf_counter() - started) * 1000
            before = process_resources(process.pid)
            sampled = time.perf_counter()
            Event().wait(seconds)
            after = process_resources(process.pid)
            duration = time.perf_counter() - sampled
            code = process.wait(timeout=5)
            if code != 0:
                raise RuntimeError("Probe failed to exit")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
    first, last = before["cpu_seconds"], after["cpu_seconds"]
    cpu = (last - first) / duration * 100 if first is not None and last is not None else None
    return {
        "scope": scope,
        "sample_seconds": duration,
        "fresh_startup_ready_ms": startup,
        "cold_cache_verified": False,
        "representative_hardware_verified": False,
        "idle_cpu_percent_one_core": cpu,
        "idle_cpu_percent_host": cpu / (os.cpu_count() or 1) if cpu is not None else None,
        "before": before,
        "after": after,
        "exit_code": code,
        "method": "50ms readiness polling; finite mock process; two CPU/memory snapshots",
        "microphone_activated": False,
        "network_requested": False,
    }
