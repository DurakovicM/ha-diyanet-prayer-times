"""Tests for the Diyanet API client and parsing."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from custom_components.diyanet_prayer_times.api import (
    DiyanetClient,
    DiyanetConnectionError,
    parse_times,
)
from custom_components.diyanet_prayer_times.const import BASE_URL, PRAYERS

from .conftest import load_fixture

TR = timezone(timedelta(hours=3))
ISTANBUL = ZoneInfo("Europe/Istanbul")
SARAJEVO = ZoneInfo("Europe/Sarajevo")


def _day(date_str: str, **times: str) -> dict:
    """A raw day as the mirror sends it (always claiming GMT+3)."""
    base = {
        "MiladiTarihKisa": date_str,
        "GreenwichOrtalamaZamani": 3.0,
        "Imsak": "05:09",
        "Gunes": "06:40",
        "Ogle": "12:47",
        "Ikindi": "15:59",
        "Aksam": "18:44",
        "Yatsi": "20:08",
    }
    return base | times


def test_parse_times_istanbul(raw_times) -> None:
    """Official times are converted to aware datetimes in the city's offset."""
    days = parse_times(raw_times, ISTANBUL)

    assert len(days) == 32
    day = next(d for d in days if d.date == date(2026, 9, 26))
    assert day.times["imsak"] == datetime(2026, 9, 26, 5, 23, tzinfo=TR)
    assert day.times["sunrise"] == datetime(2026, 9, 26, 6, 48, tzinfo=TR)
    assert day.times["dhuhr"] == datetime(2026, 9, 26, 13, 1, tzinfo=TR)
    assert day.times["asr"] == datetime(2026, 9, 26, 16, 22, tzinfo=TR)
    assert day.times["maghrib"] == datetime(2026, 9, 26, 19, 3, tzinfo=TR)
    assert day.times["isha"] == datetime(2026, 9, 26, 20, 22, tzinfo=TR)
    assert set(day.times) == set(PRAYERS)
    assert day.hijri == "15 Rebiulahir 1448"
    assert day.hijri_date == (15, 4, 1448)
    assert day.moon_url.startswith("https://")
    assert day.qibla_time is not None


def test_parse_times_uses_location_time_zone_not_gmt_field() -> None:
    """The mirror reports GMT+3 for every city; times are local wall-clock.

    Banja Luka's Dhuhr at 12:47 is 12:47 in Sarajevo time (UTC+2 in
    September), not 12:47 Turkish time (which would be an hour early).
    """
    day = parse_times([_day("29.09.2026")], SARAJEVO)[0]
    assert day.times["dhuhr"] == datetime(2026, 9, 29, 12, 47, tzinfo=SARAJEVO)
    assert day.times["dhuhr"].astimezone(timezone.utc).hour == 10
    assert day.hijri is None
    assert day.hijri_date is None


def test_parse_times_handles_dst_change() -> None:
    """After the switch to winter time (25.10.2026) the offset is +1."""
    before, after = parse_times(
        [_day("24.10.2026"), _day("26.10.2026")], SARAJEVO
    )
    assert before.times["dhuhr"].utcoffset() == timedelta(hours=2)
    assert after.times["dhuhr"].utcoffset() == timedelta(hours=1)


def test_parse_times_skips_bad_entries(raw_times) -> None:
    """Malformed days are skipped instead of failing the whole response."""
    broken = [{"MiladiTarihKisa": "garbage"}, {"Imsak": "05:00"}, *raw_times]
    assert len(parse_times(broken, ISTANBUL)) == 32


async def test_client_fetches_locations_and_times(aioclient_mock, hass) -> None:
    """Client hits the expected endpoints and parses responses."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    aioclient_mock.get(f"{BASE_URL}/ulkeler", json=load_fixture("ulkeler.json"))
    aioclient_mock.get(f"{BASE_URL}/sehirler/2", json=load_fixture("sehirler_2.json"))
    aioclient_mock.get(
        f"{BASE_URL}/ilceler/539", json=load_fixture("ilceler_539.json")
    )
    aioclient_mock.get(
        f"{BASE_URL}/vakitler/9541", json=load_fixture("vakitler_9541.json")
    )
    client = DiyanetClient(async_get_clientsession(hass))

    countries = await client.async_get_countries()
    assert countries["2"] == "TÜRKİYE"
    states = await client.async_get_states("2")
    assert states["539"] == "ISTANBUL"
    cities = await client.async_get_cities("539")
    assert cities["9541"] == "ISTANBUL"
    raw = await client.async_get_times("9541")
    assert len(parse_times(raw, ISTANBUL)) == 32


async def test_client_raises_connection_error(aioclient_mock, hass) -> None:
    """HTTP errors surface as DiyanetConnectionError."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    aioclient_mock.get(f"{BASE_URL}/vakitler/1", status=500)
    client = DiyanetClient(async_get_clientsession(hass))
    with pytest.raises(DiyanetConnectionError):
        await client.async_get_times("1")
