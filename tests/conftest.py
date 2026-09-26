"""Shared fixtures for Diyanet Prayer Times tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    """Load a recorded API response."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    return


@pytest.fixture
def raw_times() -> list[dict[str, Any]]:
    """Recorded 32-day response for Istanbul (city 9541)."""
    return load_fixture("vakitler_9541.json")
