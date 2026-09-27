"""Display texts in the integration's own language."""

from __future__ import annotations

DEFAULT_LANGUAGE = "en"

# Language code -> native name, shown in the language picker.
LANGUAGES: dict[str, str] = {
    "en": "English",
    "bs": "Bosanski",
    "de": "Deutsch",
    "nl": "Nederlands",
    "tr": "Türkçe",
}

NAMES: dict[str, dict[str, str]] = {
    "en": {
        "ezan_active": "Call to prayer active",
        "ezan": "Call to prayer",
        "imsak": "Dawn",
        "sunrise": "Sunrise",
        "dhuhr": "Noon",
        "asr": "Afternoon",
        "maghrib": "Sunset",
        "isha": "Night",
        "next_prayer": "Next prayer",
        "hijri_date": "Hijri date",
        "timestamp": "timestamp",
    },
    "bs": {
        "ezan_active": "Ezan aktivan",
        "ezan": "Ezan",
        "imsak": "Zora",
        "sunrise": "Izlazak sunca",
        "dhuhr": "Podne",
        "asr": "Ikindija",
        "maghrib": "Akšam",
        "isha": "Jacija",
        "next_prayer": "Sljedeći namaz",
        "hijri_date": "Hidžretski datum",
        "timestamp": "vremenska oznaka",
    },
    "de": {
        "ezan_active": "Gebetsruf aktiv",
        "ezan": "Gebetsruf",
        "imsak": "Morgengebet",
        "sunrise": "Sonnenaufgang",
        "dhuhr": "Mittagsgebet",
        "asr": "Nachmittagsgebet",
        "maghrib": "Abendgebet",
        "isha": "Nachtgebet",
        "next_prayer": "Nächstes Gebet",
        "hijri_date": "Hidschri-Datum",
        "timestamp": "Zeitstempel",
    },
    "nl": {
        "ezan_active": "Gebedsoproep actief",
        "ezan": "Gebedsoproep",
        "imsak": "Ochtendgebed",
        "sunrise": "Zonsopkomst",
        "dhuhr": "Middaggebed",
        "asr": "Namiddaggebed",
        "maghrib": "Avondgebed",
        "isha": "Nachtgebed",
        "next_prayer": "Volgend gebed",
        "hijri_date": "Hidjri-datum",
        "timestamp": "tijdstempel",
    },
    "tr": {
        "ezan_active": "Ezan etkin",
        "ezan": "Ezan",
        "imsak": "İmsak",
        "sunrise": "Güneş",
        "dhuhr": "Öğle",
        "asr": "İkindi",
        "maghrib": "Akşam",
        "isha": "Yatsı",
        "next_prayer": "Sonraki vakit",
        "hijri_date": "Hicri tarih",
        "timestamp": "zaman damgası",
    },
}

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
    return lang if lang in LANGUAGES else DEFAULT_LANGUAGE


def resolve_language(chosen: str | None, ha_language: str | None) -> str:
    """Return the display language for an entry's language option."""
    if chosen in (None, "auto"):
        return base_language(ha_language)
    return base_language(chosen)


def name(key: str, language: str | None) -> str:
    """Return the display name for a text key."""
    return NAMES[base_language(language)][key]


def format_hijri(day: int, month: int, year: int, language: str | None) -> str:
    """Format a Hijri date in the given language."""
    lang = base_language(language)
    name = HIJRI_MONTHS[lang][month - 1]
    sep = ". " if lang in _ORDINAL_DAY else " "
    return f"{day}{sep}{name} {year}"
