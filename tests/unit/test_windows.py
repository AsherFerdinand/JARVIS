import os
from unittest.mock import Mock

import pytest

from jarvis.actions.windows import WindowsExecutor


def test_platform_guard():
    if os.name == "nt":
        assert WindowsExecutor()
    else:
        with pytest.raises(RuntimeError):
            WindowsExecutor()


@pytest.mark.skipif(os.name != "nt", reason="Windows executor compatibility")
def test_windows_allowlist_and_launch(monkeypatch):
    child = Mock()
    child.poll.return_value = None
    launch = Mock(return_value=child)
    monkeypatch.setattr("jarvis.actions.windows.subprocess.Popen", launch)
    executor = WindowsExecutor()
    with pytest.raises(ValueError):
        executor.open_application("cmd", "cmd.exe")
    assert executor.open_application("notepad", "notepad.exe") == "notepad launched"
    executor.open_application("notepad", "notepad.exe")
    assert launch.call_count == 1
    assert launch.call_args.kwargs == {"shell": False}
    assert "System32" in launch.call_args.args[0][0]
    assert executor.application_status("notepad") == "notepad: running"
    executor.close()
    child.terminate.assert_not_called()
