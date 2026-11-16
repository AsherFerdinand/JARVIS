"""Verify runtime smokes outside the checkout, from a freshly extracted Windows ZIP."""

import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

from provider_harness import executable_pipeline


def isolated_environment() -> dict[str, str]:
    result = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("JARVIS_")
        and key not in {"VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME", "UV_PROJECT_ENVIRONMENT"}
    }
    if os.name == "nt":
        system = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        result["PATH"] = str(system / "System32") + os.pathsep + str(system)
    return result


def validate(archive: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="jarvis-extracted-") as folder:
        directory = Path(folder)
        with zipfile.ZipFile(archive) as source:
            source.extractall(directory)
        executable = directory / "JARVIS/JARVIS.exe"
        environment = isolated_environment()
        checks = []
        for args, expected in [
            (["--version"], "0.4.0"),
            (["--mock", "--command", "status"], "JARVIS ready"),
            (["--command", "system info"], "Windows"),
            (["--check-provider-worker"], "Provider worker available"),
            (["--check-audio-backend"], "Audio backend available"),
            (["--health"], '"version"'),
            (["--provider-preflight"], "offline_configuration_only"),
        ]:
            run = subprocess.run(  # noqa: S603 -- own verified extracted executable
                [str(executable), *args],
                cwd=directory,
                env=environment,  # noqa: S603
                capture_output=True,
                text=True,
                timeout=30,
            )
            if run.returncode != 0 or expected not in run.stdout:
                raise RuntimeError("Extracted executable startup/contract check failed")
            checks.append(args[0])
        run = subprocess.run(  # noqa: S603 -- own verified extracted executable
            [str(executable), "--mock-voice", "status", "--diagnostics"],  # noqa: S603
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if run.returncode != 0:
            raise RuntimeError("Extracted mock voice failed")
        voice = json.loads(run.stdout.splitlines()[-1])
        if voice["state"] != "completed" or voice["active_request_workers"] != 0:
            raise RuntimeError("Extracted mock voice did not clean up")
        devices = subprocess.run(  # noqa: S603 -- own verified extracted executable
            [str(executable), "--audio-preflight"],
            cwd=directory,
            env=environment,  # noqa: S603
            capture_output=True,
            text=True,
            timeout=30,
        )
        if devices.returncode != 0:
            raise RuntimeError("Extracted audio preflight failed")
        audio = json.loads(devices.stdout)
        if audio["streams_opened"] != 0:
            raise RuntimeError("Device preflight opened a stream")
        pipeline = executable_pipeline(executable, directory)
        return {
            "extracted_checks": checks,
            "mock_voice": voice,
            "audio_preflight": audio,
            "http_pipeline": pipeline,
            "development_environment_used_by_executable": False,
        }
