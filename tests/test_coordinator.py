"""Tests for setup, caching and the coordinator."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.diyanet_prayer_times.const import BASE_URL, DOMAIN

from .conftest import load_fixture

TR = timezone(timedelta(hours=3))
NOW = datetime(2026, 9, 26, 14, 0, tzinfo=TR)
TIMES_URL = f"{BASE_URL}/vakitler/9541"


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    """A configured Istanbul entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="9541",
        title="ISTANBUL",
        data={
            "country_id": "2",
            "country_name": "TÜRKİYE",
            "state_id": "539",
            "state_name": "ISTANBUL",
            "city_id": "9541",
            "city_name": "ISTANBUL",
        },
    )
    entry.add_to_hass(hass)
    return entry


@pytest.mark.freeze_time(NOW)
async def test_setup_fetches_and_stores(
    hass: HomeAssistant, aioclient_mock, entry, hass_storage
) -> None:
    """A successful fetch is persisted for offline use."""
    aioclient_mock.get(TIMES_URL, json=load_fixture("vakitler_9541.json"))

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    stored = hass_storage[f"{DOMAIN}.9541"]["data"]["times"]
    assert len(stored) == 32
    coordinator = entry.runtime_data
    assert coordinator.today().times["dhuhr"] == datetime(2026, 9, 26, 13, 1, tzinfo=TR)
    assert coordinator.next_prayer() == (
        "asr",
        datetime(2026, 9, 26, 16, 22, tzinfo=TR),
    )


@pytest.mark.freeze_time(NOW)
async def test_offline_start_uses_cache(
    hass: HomeAssistant, aioclient_mock, entry, hass_storage
) -> None:
    """If the source is down but the cache covers today, setup succeeds."""
    hass_storage[f"{DOMAIN}.9541"] = {
        "version": 1,
        "key": f"{DOMAIN}.9541",
        "data": {"times": load_fixture("vakitler_9541.json")},
    }
    aioclient_mock.get(TIMES_URL, status=500)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.today() is not None


@pytest.mark.freeze_time(NOW)
async def test_no_cache_and_offline_retries(
    hass: HomeAssistant, aioclient_mock, entry
) -> None:
    """Without any data the entry retries later."""
    aioclient_mock.get(TIMES_URL, status=500)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.freeze_time(NOW)
async def test_failed_refresh_keeps_data(
    hass: HomeAssistant,
    aioclient_mock,
    entry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A later failed refresh keeps the last good times available."""
    aioclient_mock.get(TIMES_URL, json=load_fixture("vakitler_9541.json"))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.clear_requests()
    aioclient_mock.get(TIMES_URL, status=500)
    freezer.tick(timedelta(hours=13))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data
    assert coordinator.last_update_success
    assert coordinator.today() is not None
