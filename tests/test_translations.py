"""Every translation must cover exactly the keys of strings.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

COMPONENT = (
    Path(__file__).parent.parent / "custom_components" / "diyanet_prayer_times"
)
LANGUAGES = ["bs", "de", "en", "nl", "tr"]


def _keys(data: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in data.items():
        path = f"{prefix}.{key}"
        keys |= _keys(value, path) if isinstance(value, dict) else {path}
    return keys


def _value(data: dict, path: str) -> str:
    for part in path.strip(".").split("."):
        data = data[part]
    return data


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("language", LANGUAGES)
def test_translation_matches_strings(language: str) -> None:
    """Translations have the same keys as strings.json and no empty values."""
    strings = _load(COMPONENT / "strings.json")
    translation = _load(COMPONENT / "translations" / f"{language}.json")
    assert _keys(translation) == _keys(strings)
    assert all(_value(translation, key) for key in _keys(translation))


def test_english_is_strings() -> None:
    """translations/en.json is identical to strings.json."""
    assert _load(COMPONENT / "translations" / "en.json") == _load(
        COMPONENT / "strings.json"
    )
