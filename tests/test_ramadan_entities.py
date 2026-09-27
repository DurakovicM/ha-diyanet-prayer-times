"""Tests for the Ramadan and religious day entities."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.diyanet_prayer_times.const import BASE_URL, DOMAIN

from .conftest import load_fixture

TR = timezone(timedelta(hours=3))


def _ramadan_raw(start: date, hijri_day: int, count: int = 32) -> list[dict[str, Any]]:
    """Raw mirror days starting at `hijri_day` Ramadan 1448 (29-day month)."""
    raw, mday, month = [], hijri_day, 9
    for offset in range(count):
        day = start + timedelta(days=offset)
        raw.append(
            {
                "MiladiTarihKisa": day.strftime("%d.%m.%Y"),
                "HicriTarihKisa": f"{mday}.{month}.1448",
                "GreenwichOrtalamaZamani": 3.0,
                "Imsak": "05:40",
                "Gunes": "07:05",
                "Ogle": "12:40",
                "Ikindi": "15:40",
                "Aksam": "18:10",
                "Yatsi": "19:30",
            }
        )
        mday += 1
        if mday > (29 if month == 9 else 30):
            mday, month = 1, month + 1
    return raw


async def _setup(hass: HomeAssistant, aioclient_mock, raw, options=None) -> None:
    aioclient_mock.get(f"{BASE_URL}/vakitler/9541", json=raw)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="9541",
        title="ISTANBUL",
        data={"city_id": "9541", "city_name": "ISTANBUL"},
        options={"time_zone": "Europe/Istanbul"} | (options or {}),
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.freeze_time(datetime(2026, 9, 26, 14, 0, tzinfo=TR))
async def test_outside_ramadan(hass: HomeAssistant, aioclient_mock) -> None:
    """In September 2026 Ramadan is off and its start is estimated."""
    await _setup(hass, aioclient_mock, load_fixture("vakitler_9541.json"))

    assert hass.states.get("binary_sensor.istanbul_ramadan").state == "off"
    days = hass.states.get("sensor.istanbul_days_until_ramadan")
    assert 130 <= int(days.state) <= 136
    assert days.attributes["unit_of_measurement"] == "d"
    assert days.attributes["estimated"] is True
    religious = hass.states.get("sensor.istanbul_religious_day")
    assert religious.state == "None"
    assert religious.attributes["key"] == "none"


@pytest.mark.freeze_time(datetime(2027, 3, 5, 14, 0, tzinfo=TR))
async def test_during_ramadan_on_laylat_al_qadr(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """On 26 Ramadan: Ramadan is on, day 26, and it is Kadir Gecesi."""
    await _setup(
        hass,
        aioclient_mock,
        _ramadan_raw(date(2027, 3, 1), 22),
        options={"language": "tr"},
    )

    ramadan = hass.states.get("binary_sensor.istanbul_ramadan")
    assert ramadan.state == "on"
    assert ramadan.attributes["day"] == 26
    assert ramadan.attributes["first_day"] == "2027-02-08"
    assert ramadan.attributes["last_day"] == "2027-03-08"
    assert ramadan.attributes["friendly_name"] == "ISTANBUL Ramazan"
    assert hass.states.get("sensor.istanbul_days_until_ramadan").state == "0"

    religious = hass.states.get("sensor.istanbul_religious_day")
    assert religious.state == "Kadir Gecesi"
    assert religious.attributes["key"] == "qadr"
    assert religious.attributes["next"] == "Ramazan Bayramı Arifesi"
    assert religious.attributes["next_date"] == "2027-03-08"


@pytest.mark.freeze_time(datetime(2027, 3, 10, 14, 0, tzinfo=TR))
async def test_eid_day_number(hass: HomeAssistant, aioclient_mock) -> None:
    """The second day of Eid is shown with its number."""
    await _setup(
        hass,
        aioclient_mock,
        _ramadan_raw(date(2027, 3, 1), 22),
        options={"language": "bs"},
    )

    assert hass.states.get("binary_sensor.istanbul_ramadan").state == "off"
    religious = hass.states.get("sensor.istanbul_religious_day")
    assert religious.state == "Ramazanski bajram, 2. dan"
    assert religious.attributes["key"] == "eid_al_fitr"
