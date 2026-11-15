"""OS effects isolated behind an injectable interface. Never uses a shell."""

import os
import subprocess
import webbrowser
from typing import Protocol


class Executor(Protocol):
    def open_website(self, url: str) -> str: ...
    def open_application(self, name: str, executable: str) -> str: ...
    def application_status(self, name: str) -> str: ...
    def close(self) -> None: ...


class MockExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def open_website(self, url: str) -> str:
        self.calls.append(("website", url))
        return "Website opened (mock)"

    def open_application(self, name: str, executable: str) -> str:
        self.calls.append(("application", executable))
        return f"{name} opened (mock)"

    def application_status(self, name: str) -> str:
        return f"{name}: mock status"

    def close(self) -> None:
        pass


class WindowsExecutor:
    def __init__(self) -> None:
        if os.name != "nt":
            raise RuntimeError("Windows executor requires Windows; use --mock on other platforms")
        self._children: dict[str, subprocess.Popen[bytes]] = {}

    def open_website(self, url: str) -> str:
        if not url.startswith("https://"):
            raise ValueError("Only HTTPS websites supported")
        if not webbrowser.open(url):
            raise RuntimeError("Browser could not open website")
        return "Website opened"

    def open_application(self, name: str, executable: str) -> str:
        # Resolve the built-in allowlist against the Windows system directory;
        # never search the current working directory or accept arguments.
        if executable != "notepad.exe":
            raise ValueError("Unsupported Windows executable")
        running = self._children.get(name)
        if running is not None and running.poll() is None:
            return f"{name} already running"
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        path = os.path.join(system_root, "System32", executable)
        self._children[name] = subprocess.Popen([path], shell=False)  # noqa: S603
        return f"{name} launched"

    def application_status(self, name: str) -> str:
        child = self._children.get(name)
        state = (
            "running" if child is not None and child.poll() is None else "not tracked as running"
        )
        return f"{name}: {state}"

    def close(self) -> None:
        # User applications intentionally outlive the assistant.
        self._children.clear()
