"""Tests for the sensors."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.diyanet_prayer_times.const import BASE_URL, DOMAIN

from .conftest import load_fixture

TR = timezone(timedelta(hours=3))
AFTERNOON = datetime(2026, 9, 26, 14, 0, tzinfo=TR)


def _utc_iso(hour: int, minute: int, day: int = 26) -> str:
    local = datetime(2026, 9, day, hour, minute, tzinfo=TR)
    return local.astimezone(timezone.utc).isoformat()


async def _setup(
    hass: HomeAssistant, aioclient_mock, options: dict[str, Any] | None = None
) -> MockConfigEntry:
    aioclient_mock.get(
        f"{BASE_URL}/vakitler/9541", json=load_fixture("vakitler_9541.json")
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="9541",
        title="ISTANBUL",
        data={"city_id": "9541", "city_name": "ISTANBUL", "state_name": "ISTANBUL"},
        options={"time_zone": "Europe/Istanbul"} | (options or {}),
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _name(hass: HomeAssistant, entity_id: str) -> str:
    return hass.states.get(entity_id).attributes["friendly_name"]


@pytest.mark.freeze_time(AFTERNOON)
async def test_clock_sensors_show_exact_times(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """Plain sensors show the published HH:MM with English names."""
    await _setup(hass, aioclient_mock)

    expected = {
        "sensor.istanbul_imsak_time": ("Dawn", "05:23"),
        "sensor.istanbul_sunrise_time": ("Sunrise", "06:48"),
        "sensor.istanbul_dhuhr_time": ("Noon", "13:01"),
        "sensor.istanbul_asr_time": ("Afternoon", "16:22"),
        "sensor.istanbul_maghrib_time": ("Sunset", "19:03"),
        "sensor.istanbul_isha_time": ("Night", "20:22"),
        "sensor.istanbul_next_prayer_time": ("Next prayer", "Afternoon 16:22"),
    }
    for entity_id, (name, value) in expected.items():
        assert hass.states.get(entity_id).state == value, entity_id
        assert _name(hass, entity_id) == f"ISTANBUL {name}"

    assert hass.states.get("sensor.istanbul_next_prayer_time").attributes[
        "prayer"
    ] == "asr"
    hijri = hass.states.get("sensor.istanbul_hijri_date")
    assert hijri.state == "15 Rabi al-Thani 1448"
    assert hijri.attributes["qibla_time"] == "11:36"
    assert hijri.attributes["entity_picture"].startswith("https://")


@pytest.mark.freeze_time(AFTERNOON)
async def test_timestamp_sensors_for_automations(
    hass: HomeAssistant, aioclient_mock, entity_registry: er.EntityRegistry
) -> None:
    """Timestamp sensors keep their IDs and are diagnostic."""
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
        assert entity_registry.async_get(entity_id).entity_category == "diagnostic"

    assert _name(hass, "sensor.istanbul_maghrib") == "ISTANBUL Sunset timestamp"
    assert hass.states.get("sensor.istanbul_maghrib").attributes["time"] == "19:03"
    next_prayer = hass.states.get("sensor.istanbul_next_prayer")
    assert next_prayer.attributes == next_prayer.attributes | {
        "prayer": "asr",
        "time": "16:22",
    }


@pytest.mark.freeze_time(AFTERNOON)
async def test_follows_ha_language_by_default(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """Without an override, names follow Home Assistant's language."""
    hass.config.language = "bs"
    await _setup(hass, aioclient_mock)

    assert _name(hass, "sensor.istanbul_maghrib_time") == "ISTANBUL Akšam"
    assert hass.states.get("sensor.istanbul_hijri_date").state == (
        "15. Rebiu-l-ahir 1448"
    )


@pytest.mark.freeze_time(AFTERNOON)
async def test_language_override(hass: HomeAssistant, aioclient_mock) -> None:
    """The integration's own language wins over Home Assistant's."""
    await _setup(hass, aioclient_mock, options={"language": "tr"})

    assert _name(hass, "sensor.istanbul_maghrib_time") == "ISTANBUL Akşam"
    assert hass.states.get("sensor.istanbul_next_prayer_time").state == (
        "İkindi 16:22"
    )
    assert hass.states.get("sensor.istanbul_hijri_date").state == (
        "15 Rebiülahir 1448"
    )


@pytest.mark.freeze_time(AFTERNOON)
async def test_options_flow_changes_language(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """Changing the language in Configure renames the sensors immediately."""
    entry = await _setup(hass, aioclient_mock)
    assert _name(hass, "sensor.istanbul_maghrib_time") == "ISTANBUL Sunset"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"language": "de", "time_zone": "Europe/Istanbul"}
    )
    await hass.async_block_till_done()

    assert entry.options["language"] == "de"
    assert _name(hass, "sensor.istanbul_maghrib_time") == "ISTANBUL Abendgebet"


@pytest.mark.freeze_time(datetime(2026, 9, 26, 20, 0, tzinfo=TR))
async def test_next_prayer_and_day_rollover(
    hass: HomeAssistant, aioclient_mock, freezer: FrozenDateTimeFactory
) -> None:
    """After Isha the next prayer is tomorrow's Imsak; at midnight times roll over."""
    await _setup(hass, aioclient_mock)
    assert hass.states.get("sensor.istanbul_next_prayer_time").state == "Night 20:22"

    freezer.move_to(datetime(2026, 9, 26, 20, 22, 1, tzinfo=TR))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.istanbul_next_prayer").attributes[
        "prayer"
    ] == "imsak"
    tomorrow_imsak = hass.states.get("sensor.istanbul_next_prayer").state
    assert hass.states.get("sensor.istanbul_imsak").state == _utc_iso(5, 23)

    freezer.move_to(datetime(2026, 9, 27, 0, 0, 2, tzinfo=TR))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.istanbul_imsak").state == tomorrow_imsak
    assert tomorrow_imsak.startswith("2026-09-27")


@pytest.mark.freeze_time(datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc))
async def test_defaults_to_home_assistant_time_zone(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """Without a time zone option, times are read in HA's time zone.

    Regression: the source claims GMT+3 for every city, which made
    European cities trigger an hour early.
    """
    await hass.config.async_set_time_zone("Europe/Sarajevo")
    aioclient_mock.get(
        f"{BASE_URL}/vakitler/9541", json=load_fixture("vakitler_9541.json")
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="9541",
        title="ISTANBUL",
        data={"city_id": "9541", "city_name": "ISTANBUL"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # 19:03 local in Sarajevo (UTC+2) is 17:03 UTC, not 16:03.
    assert hass.states.get("sensor.istanbul_maghrib").state == (
        "2026-09-26T17:03:00+00:00"
    )
    assert hass.states.get("sensor.istanbul_maghrib_time").state == "19:03"
