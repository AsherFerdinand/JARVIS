"""Tests may use only synthetic provider bindings, never inherited live credentials."""

import os

import pytest


@pytest.fixture(autouse=True)
def isolate_provider_configuration(monkeypatch):
    for name in tuple(os.environ):
        if name.startswith("JARVIS_"):
            monkeypatch.delenv(name, raising=False)
