"""Small explicit process snapshots, never a polling service."""

import ctypes
import os
from ctypes import wintypes
from pathlib import Path


def process_resources(pid: int | None = None) -> dict[str, int | float | None]:
    target = pid or os.getpid()
    if os.name == "nt":

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                (name, ctypes.c_size_t)
                for name in (
                    "peak_ws",
                    "working_set",
                    "peak_paged",
                    "paged",
                    "peak_nonpaged",
                    "nonpaged",
                    "pagefile",
                    "peak_pagefile",
                    "private",
                )
            ]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
        psapi = ctypes.WinDLL("psapi", use_last_error=True)  # type: ignore[attr-defined]
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
            ctypes.POINTER(wintypes.FILETIME)
        ] * 4
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(Counters),
            wintypes.DWORD,
        ]
        handle = kernel.OpenProcess(0x0400 | 0x0010, False, target)
        if not handle:
            raise OSError("Process metrics unavailable")
        try:
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                raise OSError("Process memory unavailable")
            times = [wintypes.FILETIME() for _ in range(4)]
            if not kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
                raise OSError("Process CPU unavailable")
            cpu = sum((t.dwHighDateTime << 32) | t.dwLowDateTime for t in times[2:]) / 10_000_000
            return {
                "working_set_bytes": counters.working_set,
                "peak_working_set_bytes": counters.peak_ws,
                "private_bytes": counters.private,
                "cpu_seconds": cpu,
            }
        finally:
            kernel.CloseHandle(handle)
    try:
        status = Path(f"/proc/{target}/status").read_text()
        rss = next(
            int(line.split()[1]) * 1024 for line in status.splitlines() if line.startswith("VmRSS:")
        )
        fields = Path(f"/proc/{target}/stat").read_text().rsplit(") ", 1)[1].split()
        cpu = (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")
        return {"working_set_bytes": rss, "private_bytes": None, "cpu_seconds": cpu}
    except (OSError, ValueError, StopIteration, IndexError):
        return {"working_set_bytes": None, "private_bytes": None, "cpu_seconds": None}
