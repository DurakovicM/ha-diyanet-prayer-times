"""Constants for the Diyanet Prayer Times integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "diyanet_prayer_times"

BASE_URL: Final = "https://ezanvakti.emushaf.net"
REQUEST_TIMEOUT: Final = 20
UPDATE_INTERVAL: Final = timedelta(hours=12)

CONF_COUNTRY_ID: Final = "country_id"
CONF_STATE_ID: Final = "state_id"
CONF_CITY_ID: Final = "city_id"
CONF_COUNTRY_NAME: Final = "country_name"
CONF_STATE_NAME: Final = "state_name"
CONF_CITY_NAME: Final = "city_name"
CONF_LANGUAGE: Final = "language"
LANGUAGE_AUTO: Final = "auto"

# Prayer key -> field name in the Diyanet response, in daily order.
PRAYERS: Final[dict[str, str]] = {
    "imsak": "Imsak",
    "sunrise": "Gunes",
    "dhuhr": "Ogle",
    "asr": "Ikindi",
    "maghrib": "Aksam",
    "isha": "Yatsi",
}
