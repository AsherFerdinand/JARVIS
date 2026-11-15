"""Publish sanitized pytest counts/failure identities, never assertion text or captured output."""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def report(path: Path) -> dict[str, object]:
    root = ET.parse(path).getroot()  # noqa: S314 -- own pytest output; no external source
    suites = list(root.iter("testsuite"))
    counts = {
        key: sum(int(suite.get(key, "0")) for suite in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    if counts["tests"] == 0:
        raise ValueError("No test results recorded")
    failures = []
    for case in root.iter("testcase"):
        failure = case.find("failure")
        if failure is None:
            failure = case.find("error")
        if failure is None:
            continue
        name = case.get("name", "unknown").split("[", 1)[0]
        identity = re.sub(r"[^a-zA-Z0-9_.]", "_", name)[:100]
        message = failure.get("message", "")
        codes = sorted(
            set(
                re.findall(
                    r"\b(?:request_deadline|connection_timeout|response_timeout|"
                    r"transport_failure|tls_error|partial_response|transport_busy)\b",
                    message,
                )
            )
        )
        # Numeric comparisons help diagnose timing assertions, without publishing assertion strings.
        comparisons = re.findall(r"assert\s+([0-9.]+)\s*(?:<=|>=|<|>|==)\s*([0-9.]+)", message)
        numbers = [number for pair in comparisons[:4] for number in pair]
        failures.append(
            {
                "test": identity,
                "error_type": re.sub(r"[^a-zA-Z0-9_.]", "_", failure.get("type", "unknown"))[:80],
                "codes": codes,
                "numbers": numbers,
            }
        )
    return {"counts": counts, "failed_tests": failures}


if __name__ == "__main__":
    result = report(Path(sys.argv[1]))
    print("::notice title=Sanitized test results::" + json.dumps(result))
