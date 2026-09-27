"""Client for the Diyanet prayer times mirror (ezanvakti.emushaf.net)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, time, tzinfo
import logging
from typing import Any

import aiohttp

from .const import BASE_URL, PRAYERS, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class DiyanetConnectionError(Exception):
    """Raised when the API cannot be reached or returns an error."""


@dataclass(frozen=True, slots=True)
class DayTimes:
    """Official prayer times for a single day."""

    date: date
    times: dict[str, datetime]
    hijri: str | None
    hijri_date: tuple[int, int, int] | None
    moon_url: str | None
    qibla_time: str | None


def _parse_hijri(value: str | None) -> tuple[int, int, int] | None:
    """Parse 'd.m.yyyy' into (day, month, year)."""
    try:
        day, month, year = (int(part) for part in value.split("."))
    except (AttributeError, ValueError):
        return None
    if not 1 <= month <= 12:
        return None
    return day, month, year


def _parse_day(raw: dict[str, Any], tz: tzinfo) -> DayTimes:
    # Times are local wall-clock at the location. The response's
    # GreenwichOrtalamaZamani is always 3.0 (Turkey), so it is ignored.
    day = datetime.strptime(raw["MiladiTarihKisa"], "%d.%m.%Y").date()
    times = {
        key: datetime.combine(day, time.fromisoformat(raw[field]), tzinfo=tz)
        for key, field in PRAYERS.items()
    }
    return DayTimes(
        date=day,
        times=times,
        hijri=raw.get("HicriTarihUzun"),
        hijri_date=_parse_hijri(raw.get("HicriTarihKisa")),
        moon_url=raw.get("AyinSekliURL"),
        qibla_time=raw.get("KibleSaati"),
    )


def parse_times(raw: list[dict[str, Any]], tz: tzinfo) -> list[DayTimes]:
    """Parse a /vakitler response in the location's time zone.

    Malformed days are skipped.
    """
    days: list[DayTimes] = []
    for entry in raw:
        try:
            days.append(_parse_day(entry, tz))
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.warning("Skipping unparseable day %s: %s", entry, err)
    return sorted(days, key=lambda d: d.date)


class DiyanetClient:
    """Thin async wrapper around the mirror's endpoints."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the client."""
        self._session = session

    async def _get(self, path: str) -> Any:
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                resp = await self._session.get(f"{BASE_URL}/{path}")
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise DiyanetConnectionError(f"Request to /{path} failed: {err}") from err

    async def _get_places(self, path: str, prefix: str) -> dict[str, str]:
        data = await self._get(path)
        return {
            item[f"{prefix}ID"]: item.get(f"{prefix}AdiEn") or item[f"{prefix}Adi"]
            for item in data
        }

    async def async_get_countries(self) -> dict[str, str]:
        """Return {country_id: name}."""
        return await self._get_places("ulkeler", "Ulke")

    async def async_get_states(self, country_id: str) -> dict[str, str]:
        """Return {state_id: name} for a country."""
        return await self._get_places(f"sehirler/{country_id}", "Sehir")

    async def async_get_cities(self, state_id: str) -> dict[str, str]:
        """Return {city_id: name} for a state."""
        return await self._get_places(f"ilceler/{state_id}", "Ilce")

    async def async_get_times(self, city_id: str) -> list[dict[str, Any]]:
        """Return the raw ~32-day prayer time list for a city."""
        data = await self._get(f"vakitler/{city_id}")
        if not isinstance(data, list):
            raise DiyanetConnectionError(f"Unexpected response for city {city_id}")
        return data
