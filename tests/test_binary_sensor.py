"""Tests for the ezan binary sensor."""

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
EZAN = "binary_sensor.istanbul_ezan"


async def _setup(hass: HomeAssistant, aioclient_mock, options=None) -> None:
    aioclient_mock.get(
        f"{BASE_URL}/vakitler/9541", json=load_fixture("vakitler_9541.json")
    )
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


async def _at(hass: HomeAssistant, freezer: FrozenDateTimeFactory, when) -> None:
    freezer.move_to(when)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


@pytest.mark.freeze_time(datetime(2026, 9, 26, 16, 0, tzinfo=TR))
async def test_on_for_one_minute_at_prayer_time(
    hass: HomeAssistant, aioclient_mock, freezer: FrozenDateTimeFactory
) -> None:
    """The sensor detects 'motion' for one minute starting at Asr."""
    await _setup(hass, aioclient_mock)
    state = hass.states.get(EZAN)
    assert state.state == "off"
    assert state.attributes["device_class"] == "motion"
    assert state.attributes["friendly_name"] == "ISTANBUL Call to prayer"

    await _at(hass, freezer, datetime(2026, 9, 26, 16, 22, 0, 500, tzinfo=TR))
    state = hass.states.get(EZAN)
    assert state.state == "on"
    assert state.attributes["prayer"] == "asr"

    await _at(hass, freezer, datetime(2026, 9, 26, 16, 23, 0, 500, tzinfo=TR))
    state = hass.states.get(EZAN)
    assert state.state == "off"
    assert state.attributes["prayer"] is None


@pytest.mark.freeze_time(datetime(2026, 9, 26, 6, 40, tzinfo=TR))
async def test_not_on_at_sunrise(
    hass: HomeAssistant, aioclient_mock, freezer: FrozenDateTimeFactory
) -> None:
    """Sunrise is not a prayer, so no ezan."""
    await _setup(hass, aioclient_mock)
    await _at(hass, freezer, datetime(2026, 9, 26, 6, 48, 0, 500, tzinfo=TR))
    assert hass.states.get(EZAN).state == "off"


@pytest.mark.freeze_time(datetime(2026, 9, 26, 16, 0, tzinfo=TR))
async def test_name_follows_integration_language(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """The name uses the integration's language."""
    await _setup(hass, aioclient_mock, options={"language": "bs"})
    assert hass.states.get(EZAN).attributes["friendly_name"] == "ISTANBUL Ezan"
