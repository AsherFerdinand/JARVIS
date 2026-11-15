"""Bounded synthetic stress, retained allocation and worker startup profile."""

import gc
import json
import multiprocessing
import time
import tracemalloc

from jarvis.actions.windows import MockExecutor
from jarvis.config import Config
from jarvis.core.lifecycle import Assistant
from jarvis.intelligence.transport import ProcessTransport
from jarvis.speech.setup import make_voice


def main() -> None:
    assistant = Assistant(Config(), MockExecutor())
    controller = make_voice(assistant, mock_text="open youtube")
    tracemalloc.start()
    for _ in range(10):
        controller.start()
        controller.wait(5)
    gc.collect()
    before = tracemalloc.get_traced_memory()[0]
    started = time.perf_counter()
    for _ in range(200):
        controller.start()
        controller.wait(5)
    elapsed = (time.perf_counter() - started) * 1000
    gc.collect()
    after, peak = tracemalloc.get_traced_memory()
    controller.close()
    tracemalloc.stop()
    samples = []
    for _ in range(3):
        started = time.perf_counter()
        worker_resources = ProcessTransport().probe()
        samples.append((time.perf_counter() - started) * 1000)
    print(
        json.dumps(
            {
                "sessions": 200,
                "mock_elapsed_ms": elapsed,
                "retained_bytes_delta": after - before,
                "traced_peak_bytes": peak,
                "event_count": len(assistant.events.snapshot()),
                "mock_effect_history": len(assistant.executor.calls),
                "provider_probe_ms": samples,
                "last_probe_worker_resources": worker_resources,
                "active_request_workers": len(multiprocessing.active_children()),
                "limitations": "synthetic audio; no hardware/network; POSIX resource tracker may "
                "remain after first spawn; import/startup cost is not idle CPU",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
