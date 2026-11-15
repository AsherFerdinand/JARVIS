"""Synthetic pipeline latency and optional import RSS; never opens audio devices."""

import json
import subprocess
import sys
import time
import tracemalloc
from importlib.metadata import PackageNotFoundError, distribution

from jarvis.actions.windows import MockExecutor
from jarvis.config import Config
from jarvis.core.lifecycle import Assistant
from jarvis.speech.audio import encode_wav
from jarvis.speech.setup import make_voice

tracemalloc.start()
assistant = Assistant(Config(), MockExecutor())
controller = make_voice(assistant, mock_text="Open YouTube.")
started = time.perf_counter()
for _ in range(20):
    controller.start()
    result = controller.wait(5)
    if result.state.current != "completed":
        raise RuntimeError("Mock voice benchmark failed")
audio = encode_wav(b"\x10\x00" * (16000 * 60))
current, peak = tracemalloc.get_traced_memory()
controller.close()

report: dict[str, object] = {
    "platform": sys.platform,
    "mock_sessions": 20,
    "elapsed_ms": (time.perf_counter() - started) * 1000,
    "last_session_timings_ms": result.timings_ms,
    "python_peak_bytes": peak,
    "max_capture_wav_bytes": len(audio),
    "hardware_or_network_measured": False,
}
if sys.platform == "linux":
    # ru_maxrss is KiB on Linux; isolated child processes avoid retaining one import's peak.
    measurements = {}
    for label, module in [("core", "jarvis.core.lifecycle"), ("audio_import", "sounddevice")]:
        probe = subprocess.run(  # noqa: S603 -- fixed interpreter/modules
            [
                sys.executable,
                "-c",
                "import importlib, resource, json; import jarvis.core.lifecycle; "
                f"importlib.import_module('{module}'); "
                "rss = next(int(line.split()[1]) for line in open('/proc/self/status') "
                "if line.startswith('VmRSS:')); "
                "print(json.dumps({'rss_kib': rss, 'peak_rss_kib': "
                "resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        measurements[label] = json.loads(probe.stdout) if probe.returncode == 0 else None
    report["import_memory"] = measurements
    if all(measurements.values()):
        report["audio_import_rss_delta_kib"] = (
            measurements["audio_import"]["rss_kib"] - measurements["core"]["rss_kib"]
        )
sizes = {}
for package in ("sounddevice", "cffi", "pycparser"):
    try:
        installed = distribution(package)
        sizes[package] = sum(
            installed.locate_file(file).stat().st_size
            for file in installed.files or []
            if installed.locate_file(file).is_file()
        )
    except PackageNotFoundError:
        sizes[package] = None
report["optional_audio_distribution_bytes"] = sizes
print(json.dumps(report, indent=2))
