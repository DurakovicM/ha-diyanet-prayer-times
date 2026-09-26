"""Tests for the sensors."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.diyanet_prayer_times.const import BASE_URL, DOMAIN

from .conftest import load_fixture

TR = timezone(timedelta(hours=3))


def _utc_iso(hour: int, minute: int, day: int = 26) -> str:
    return datetime(2026, 9, day, hour, minute, tzinfo=TR).astimezone(timezone.utc).isoformat()


async def _setup(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(
        f"{BASE_URL}/vakitler/9541", json=load_fixture("vakitler_9541.json")
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="9541",
        title="ISTANBUL",
        data={"city_id": "9541", "city_name": "ISTANBUL", "state_name": "ISTANBUL"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.freeze_time(datetime(2026, 9, 26, 14, 0, tzinfo=TR))
async def test_prayer_sensors(hass: HomeAssistant, aioclient_mock) -> None:
    """Sensors show today's official times."""
    await _setup(hass, aioclient_mock)

    expected = {
        "sensor.istanbul_imsak": _utc_iso(5, 23),
        "sensor.istanbul_sunrise": _utc_iso(6, 48),
        "sensor.istanbul_dhuhr": _utc_iso(13, 1),
        "sensor.istanbul_asr": _utc_iso(16, 22),
        "sensor.istanbul_maghrib": _utc_iso(19, 3),
        "sensor.istanbul_isha": _utc_iso(20, 22),
        "sensor.istanbul_next_prayer": _utc_iso(16, 22),
    }
    for entity_id, value in expected.items():
        assert hass.states.get(entity_id).state == value, entity_id

    assert hass.states.get("sensor.istanbul_next_prayer").attributes["prayer"] == "asr"
    hijri = hass.states.get("sensor.istanbul_hijri_date")
    assert hijri.state == "15 Rebiulahir 1448"
    assert hijri.attributes["qibla_time"] == "11:36"
    assert hijri.attributes["entity_picture"].startswith("https://")


@pytest.mark.freeze_time(datetime(2026, 9, 26, 20, 0, tzinfo=TR))
async def test_next_prayer_and_day_rollover(
    hass: HomeAssistant, aioclient_mock, freezer: FrozenDateTimeFactory
) -> None:
    """After Isha the next prayer is tomorrow's Imsak; at midnight times roll over."""
    await _setup(hass, aioclient_mock)
    assert hass.states.get("sensor.istanbul_next_prayer").attributes["prayer"] == "isha"

    freezer.move_to(datetime(2026, 9, 26, 20, 22, 1, tzinfo=TR))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    next_prayer = hass.states.get("sensor.istanbul_next_prayer")
    assert next_prayer.attributes["prayer"] == "imsak"
    assert hass.states.get("sensor.istanbul_imsak").state == _utc_iso(5, 23)

    freezer.move_to(datetime(2026, 9, 27, 0, 0, 2, tzinfo=TR))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    tomorrow_imsak = hass.states.get("sensor.istanbul_imsak").state
    assert tomorrow_imsak == next_prayer.state
    assert tomorrow_imsak.startswith("2026-09-27")
