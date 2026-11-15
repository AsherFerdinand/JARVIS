"""Explicit configuration; no credentials persisted by JARVIS."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    websites: dict[str, str] = field(default_factory=lambda: {"youtube": "https://www.youtube.com"})
    applications: dict[str, str] = field(default_factory=lambda: {"notepad": "notepad.exe"})
    provider_url: str | None = None
    model: str | None = None
    request_timeout: float = 15.0
