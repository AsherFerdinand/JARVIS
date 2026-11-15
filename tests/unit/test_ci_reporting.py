import runpy
from pathlib import Path


def test_ci_report_does_not_publish_failure_content(tmp_path):
    path = tmp_path / "results.xml"
    path.write_text(
        '<testsuites><testsuite tests="1" failures="1" errors="0" skipped="0">'
        '<testcase name="test_request[private-key]"><failure type="AssertionError" '
        'message="private-key private-audio request_deadline 1.2 3.0">'
        "private transcript</failure></testcase></testsuite></testsuites>"
    )
    report = runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/report_tests.py"))[
        "report"
    ]
    result = report(path)
    assert result["counts"]["failures"] == 1
    assert "private" not in str(result)
    assert result["failed_tests"][0]["codes"] == ["request_deadline"]
