"""Tests for the config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.diyanet_prayer_times.const import BASE_URL, DOMAIN

from .conftest import load_fixture


def _mock_places(aioclient_mock) -> None:
    aioclient_mock.get(f"{BASE_URL}/ulkeler", json=load_fixture("ulkeler.json"))
    aioclient_mock.get(f"{BASE_URL}/sehirler/2", json=load_fixture("sehirler_2.json"))
    aioclient_mock.get(
        f"{BASE_URL}/ilceler/539", json=load_fixture("ilceler_539.json")
    )


async def _run_flow(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"country_id": "2"}
    )
    assert result["step_id"] == "state"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"state_id": "539"}
    )
    assert result["step_id"] == "city"
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"city_id": "9541"}
    )


async def test_full_flow(hass: HomeAssistant, aioclient_mock) -> None:
    """Selecting country, state and city creates an entry."""
    _mock_places(aioclient_mock)
    aioclient_mock.get(
        f"{BASE_URL}/vakitler/9541", json=load_fixture("vakitler_9541.json")
    )

    result = await _run_flow(hass)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ISTANBUL"
    assert result["data"] == {
        "country_id": "2",
        "country_name": "TÜRKİYE",
        "state_id": "539",
        "state_name": "ISTANBUL",
        "city_id": "9541",
        "city_name": "ISTANBUL",
    }
    assert result["result"].unique_id == "9541"


async def test_duplicate_city_aborts(hass: HomeAssistant, aioclient_mock) -> None:
    """A city can only be configured once."""
    MockConfigEntry(domain=DOMAIN, unique_id="9541").add_to_hass(hass)
    _mock_places(aioclient_mock)

    result = await _run_flow(hass)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_cannot_connect(hass: HomeAssistant, aioclient_mock) -> None:
    """Connection problems show an error on the form."""
    aioclient_mock.get(f"{BASE_URL}/ulkeler", status=503)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
