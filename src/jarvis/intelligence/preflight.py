"""Local contract validation only. No imports of audio backends or network calls."""

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Capabilities:
    language_hint: bool
    speaking_rate: bool


PROFILES = {"openai": Capabilities(True, True), "compatible": Capabilities(False, False)}
PATHS = {"AI": "/v1/chat/completions", "STT": "/v1/audio/transcriptions", "TTS": "/v1/audio/speech"}


def capabilities(role: str, settings: Mapping[str, str]) -> Capabilities:
    profile = settings.get(f"JARVIS_{role}_PROFILE", "openai")
    if profile not in PROFILES:
        raise ValueError("Unsupported provider profile")
    base = PROFILES[profile]
    overrides = []
    for key, default in (("LANGUAGE_HINT", base.language_hint), ("SPEED", base.speaking_rate)):
        value = settings.get(f"JARVIS_{role}_{key}")
        if value not in {None, "0", "1"}:
            raise ValueError("Capability overrides must be 0 or 1")
        overrides.append(default if value is None else value == "1")
    return Capabilities(*overrides)


class RoleReport(TypedDict):
    configured: bool
    valid: bool
    errors: list[str]
    warnings: list[str]
    capabilities: dict[str, bool]


class PreflightReport(TypedDict):
    validation: str
    network_requests: int
    live_verified: bool
    valid_configured_providers: bool
    providers: dict[str, RoleReport]


def preflight(settings: Mapping[str, str] | None = None) -> PreflightReport:
    settings = os.environ if settings is None else settings
    language = settings.get("JARVIS_VOICE_LANGUAGE", "en")
    providers: dict[str, RoleReport] = {}
    all_errors = []
    if language not in {"en", "de"}:
        all_errors.append("invalid_language")
    for role in PATHS:
        prefix = f"JARVIS_{role}"
        errors: list[str] = []
        warnings: list[str] = []
        values = {name: settings.get(f"{prefix}_{name}", "") for name in ("URL", "KEY", "MODEL")}
        configured = any(value for key, value in settings.items() if key.startswith(prefix + "_"))
        if not values["KEY"]:
            errors.append("missing_credential")
        if not values["MODEL"]:
            errors.append("missing_model")
        elif any(c in values["MODEL"] for c in '\r\n"'):
            errors.append("invalid_model")
        if not values["URL"]:
            errors.append("missing_url")
        else:
            try:
                url = urlsplit(values["URL"])
                _ = url.port
                if url.scheme != "https" or not url.hostname or url.username or url.password:
                    errors.append("invalid_url")
                if url.fragment or url.query:
                    errors.append("url_query_or_fragment_not_supported")
                if url.hostname == "api.openai.com" and url.path != PATHS[role]:
                    errors.append("unsupported_openai_path")
                if url.path != PATHS[role]:
                    # Compatible servers may use a custom prefix; not an undocumented rewrite.
                    warnings.append("custom_path_unverified")
            except ValueError:
                errors.append("invalid_url")
        if configured and not all(values.values()):
            errors.append("incomplete_configuration")
        try:
            caps = capabilities(role, settings)
        except ValueError:
            errors.append("invalid_capability_profile")
            caps = Capabilities(False, False)
        if language not in {"en", "de"}:
            errors.append("invalid_language")
        for name, default in (("TIMEOUT", "15"), ("CONNECT_TIMEOUT", "10"), ("DEADLINE", "30")):
            try:
                value = float(settings.get(f"{prefix}_{name}", default))
                if not math.isfinite(value) or not 0 < value <= 120:
                    errors.append("invalid_timeout")
            except ValueError:
                errors.append("invalid_timeout")
        if role == "STT" and settings.get("JARVIS_STT_RESPONSE_FORMAT", "json") not in {
            "json",
            "text",
        }:
            errors.append("unsupported_transcription_format")
        # Documented restrictions are validation data, never a default model selection.
        if (
            role == "STT"
            and settings.get("JARVIS_STT_PROFILE", "openai") == "openai"
            and (
                values["MODEL"] in {"gpt-4o-transcribe", "gpt-4o-mini-transcribe"}
                or values["MODEL"].startswith("gpt-4o-mini-transcribe-")
            )
            and settings.get("JARVIS_STT_RESPONSE_FORMAT", "json") != "json"
        ):
            errors.append("model_requires_json_transcription")
        if role == "TTS":
            if settings.get("JARVIS_TTS_FORMAT", "wav") != "wav":
                errors.append("unsupported_audio_format")
            if not settings.get("JARVIS_TTS_VOICE"):
                errors.append("missing_voice")
            try:
                rate = float(settings.get("JARVIS_TTS_RATE", "1"))
                if not math.isfinite(rate) or not 0.25 <= rate <= 4:
                    errors.append("invalid_speaking_rate")
                elif not caps.speaking_rate and rate != 1:
                    errors.append("speaking_rate_not_supported")
            except ValueError:
                errors.append("invalid_speaking_rate")
        if (
            role == "AI"
            and settings.get("JARVIS_AI_SCHEMA", "chat_completions") != "chat_completions"
        ):
            errors.append("unsupported_chat_schema")
        if role == "AI" and settings.get("JARVIS_AI_SYSTEM_ROLE", "system") not in {
            "system",
            "developer",
            "none",
        }:
            errors.append("unsupported_chat_instruction_role")
        warnings.append("model_and_endpoint_not_live_verified")
        providers[role] = {
            "configured": configured,
            "valid": not errors,
            "errors": sorted(set(errors)),
            "warnings": warnings,
            "capabilities": {
                "language_hint": caps.language_hint,
                "speaking_rate": caps.speaking_rate,
            },
        }
        if configured:
            all_errors.extend(errors)
    return {
        "validation": "offline_configuration_only",
        "network_requests": 0,
        "live_verified": False,
        "valid_configured_providers": not all_errors,
        "providers": providers,
    }


def require_valid(role: str, settings: Mapping[str, str]) -> None:
    item = preflight(settings)["providers"][role]
    if not item["valid"]:
        raise ValueError("Invalid provider configuration; run --provider-preflight")
