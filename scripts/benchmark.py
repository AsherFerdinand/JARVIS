"""Portable routing/core-startup measurements; not Windows idle resource proof."""

import json
import platform
import statistics
import time
import tracemalloc

from jarvis.actions.windows import MockExecutor
from jarvis.config import Config
from jarvis.core.lifecycle import Assistant

tracemalloc.start()
started = time.perf_counter()
assistant = Assistant(Config(), MockExecutor())
startup = (time.perf_counter() - started) * 1000
samples = []
for _ in range(10000):
    started = time.perf_counter()
    assistant.router.route("open youtube")
    samples.append((time.perf_counter() - started) * 1000)
current, peak = tracemalloc.get_traced_memory()
assistant.close()
print(
    json.dumps(
        {
            "platform": platform.platform(),
            "iterations": len(samples),
            "startup_ms": startup,
            "routing_median_ms": statistics.median(samples),
            "routing_p99_ms": sorted(samples)[9899],
            "python_current_bytes": current,
            "python_peak_bytes": peak,
        },
        indent=2,
    )
)
