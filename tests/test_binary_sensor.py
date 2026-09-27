"""Tests for the ezan binary sensor."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    mock_restore_cache,
)

from custom_components.diyanet_prayer_times.const import BASE_URL, DOMAIN

from .conftest import load_fixture

TR = timezone(timedelta(hours=3))
EZAN = "binary_sensor.istanbul_ezan"
SWITCH = "switch.istanbul_ezan_active"
ASR = datetime(2026, 9, 26, 16, 22, 0, 500, tzinfo=TR)
MAGHRIB = datetime(2026, 9, 26, 19, 3, 0, 500, tzinfo=TR)


async def _setup(
    hass: HomeAssistant, aioclient_mock, options=None
) -> MockConfigEntry:
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
    return entry


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


@pytest.mark.freeze_time(datetime(2026, 9, 26, 16, 0, tzinfo=TR))
async def test_only_selected_prayers_trigger(
    hass: HomeAssistant, aioclient_mock, freezer: FrozenDateTimeFactory
) -> None:
    """Unselected prayers (here Asr) do not trigger the ezan."""
    await _setup(
        hass, aioclient_mock, options={"ezan_prayers": ["imsak", "maghrib"]}
    )

    await _at(hass, freezer, ASR)
    assert hass.states.get(EZAN).state == "off"

    await _at(hass, freezer, MAGHRIB)
    state = hass.states.get(EZAN)
    assert state.state == "on"
    assert state.attributes["prayer"] == "maghrib"


@pytest.mark.freeze_time(datetime(2026, 9, 26, 16, 0, tzinfo=TR))
async def test_switch_disables_ezan(
    hass: HomeAssistant, aioclient_mock, freezer: FrozenDateTimeFactory
) -> None:
    """With the switch off the ezan never fires; turning it on re-enables it."""
    await _setup(hass, aioclient_mock)
    switch = hass.states.get(SWITCH)
    assert switch.state == "on"
    assert switch.attributes["friendly_name"] == "ISTANBUL Call to prayer active"

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": SWITCH}, blocking=True
    )
    await _at(hass, freezer, ASR)
    assert hass.states.get(SWITCH).state == "off"
    assert hass.states.get(EZAN).state == "off"

    # Turning it on during the window starts the ezan immediately.
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": SWITCH}, blocking=True
    )
    assert hass.states.get(EZAN).state == "on"


@pytest.mark.freeze_time(datetime(2026, 9, 26, 16, 0, tzinfo=TR))
async def test_switch_restores_off_after_restart(
    hass: HomeAssistant, aioclient_mock, freezer: FrozenDateTimeFactory
) -> None:
    """The switch keeps its position across restarts."""
    mock_restore_cache(hass, [State(SWITCH, "off")])
    await _setup(hass, aioclient_mock)

    assert hass.states.get(SWITCH).state == "off"
    await _at(hass, freezer, ASR)
    assert hass.states.get(EZAN).state == "off"


@pytest.mark.freeze_time(datetime(2026, 9, 26, 16, 0, tzinfo=TR))
async def test_options_flow_selects_prayers(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """Configure offers the prayers in the integration's language."""
    entry = await _setup(hass, aioclient_mock, options={"language": "bs"})

    result = await hass.config_entries.options.async_init(entry.entry_id)
    selector = result["data_schema"].schema["ezan_prayers"]
    labels = [o["label"] for o in selector.config["options"]]
    assert labels == ["Zora", "Podne", "Ikindija", "Akšam", "Jacija"]

    await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "language": "bs",
            "time_zone": "Europe/Istanbul",
            "ezan_prayers": ["imsak", "dhuhr", "maghrib"],
        },
    )
    await hass.async_block_till_done()
    assert entry.options["ezan_prayers"] == ["imsak", "dhuhr", "maghrib"]
