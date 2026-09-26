"""Localized Hijri date formatting."""

from __future__ import annotations

DEFAULT_LANGUAGE = "en"

HIJRI_MONTHS: dict[str, tuple[str, ...]] = {
    "en": (
        "Muharram", "Safar", "Rabi al-Awwal", "Rabi al-Thani",
        "Jumada al-Ula", "Jumada al-Akhirah", "Rajab", "Sha'ban",
        "Ramadan", "Shawwal", "Dhu al-Qadah", "Dhu al-Hijjah",
    ),
    "tr": (
        "Muharrem", "Safer", "Rebiülevvel", "Rebiülahir",
        "Cemaziyelevvel", "Cemaziyelahir", "Recep", "Şaban",
        "Ramazan", "Şevval", "Zilkade", "Zilhicce",
    ),
    "bs": (
        "Muharrem", "Safer", "Rebiu-l-evvel", "Rebiu-l-ahir",
        "Džumade-l-ula", "Džumade-l-uhra", "Redžeb", "Ša'ban",
        "Ramazan", "Ševval", "Zu-l-ka'de", "Zu-l-hidždže",
    ),
    "de": (
        "Muharram", "Safar", "Rabi' al-awwal", "Rabi' ath-thani",
        "Dschumada l-ula", "Dschumada th-thaniya", "Radschab", "Scha'ban",
        "Ramadan", "Schawwal", "Dhu l-qa'da", "Dhu l-hiddscha",
    ),
    "nl": (
        "Moeharram", "Safar", "Rabi al-awwal", "Rabi al-thani",
        "Djoemada al-oela", "Djoemada al-achira", "Radjab", "Sja'ban",
        "Ramadan", "Sjawwal", "Dhoe al-ka'da", "Dhoe al-hiddja",
    ),
}

# Languages that write the day as an ordinal ("15. Safar").
_ORDINAL_DAY = {"bs", "de"}


def base_language(language: str | None) -> str:
    """Map an HA language code (e.g. 'de-CH') to a supported language."""
    lang = (language or "").split("-")[0].lower()
    return lang if lang in HIJRI_MONTHS else DEFAULT_LANGUAGE


def format_hijri(day: int, month: int, year: int, language: str | None) -> str:
    """Format a Hijri date in the given language."""
    lang = base_language(language)
    name = HIJRI_MONTHS[lang][month - 1]
    sep = ". " if lang in _ORDINAL_DAY else " "
    return f"{day}{sep}{name} {year}"
