"""Tests for localized Hijri dates."""

from __future__ import annotations

import pytest

from custom_components.diyanet_prayer_times.i18n import (
    HIJRI_MONTHS,
    base_language,
    format_hijri,
)


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "15 Rabi al-Thani 1448"),
        ("tr", "15 Rebiülahir 1448"),
        ("bs", "15. Rebiu-l-ahir 1448"),
        ("de", "15. Rabi' ath-thani 1448"),
        ("nl", "15 Rabi al-thani 1448"),
    ],
)
def test_format_hijri(language: str, expected: str) -> None:
    """Month names are localized per language."""
    assert format_hijri(15, 4, 1448, language) == expected


@pytest.mark.parametrize(
    ("language", "expected"),
    [("de-CH", "de"), ("en-GB", "en"), ("fr", "en"), (None, "en"), ("BS", "bs")],
)
def test_base_language(language: str | None, expected: str) -> None:
    """Regional variants map to the base language; unknown falls back to English."""
    assert base_language(language) == expected


def test_all_languages_have_twelve_months() -> None:
    """Every language defines all twelve months."""
    assert {len(months) for months in HIJRI_MONTHS.values()} == {12}
