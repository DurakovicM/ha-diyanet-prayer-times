"""Config flow for Diyanet Prayer Times."""

from __future__ import annotations

from typing import Any
from zoneinfo import available_timezones

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from . import i18n
from .api import DiyanetClient, DiyanetConnectionError
from .const import (
    CONF_CITY_ID,
    CONF_CITY_NAME,
    CONF_COUNTRY_ID,
    CONF_COUNTRY_NAME,
    CONF_EZAN_PRAYERS,
    CONF_LANGUAGE,
    CONF_STATE_ID,
    CONF_STATE_NAME,
    CONF_TIME_ZONE,
    DAILY_PRAYERS,
    DOMAIN,
    LANGUAGE_AUTO,
)
from .i18n import LANGUAGES


def _language_selector() -> SelectSelector:
    options = [SelectOptionDict(value=LANGUAGE_AUTO, label=LANGUAGE_AUTO)]
    options += [
        SelectOptionDict(value=code, label=label) for code, label in LANGUAGES.items()
    ]
    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            mode=SelectSelectorMode.DROPDOWN,
            translation_key=CONF_LANGUAGE,
        )
    )


def _select_schema(key: str, places: dict[str, str]) -> vol.Schema:
    options = [
        SelectOptionDict(value=place_id, label=name)
        for place_id, name in sorted(places.items(), key=lambda item: item[1])
    ]
    return vol.Schema(
        {
            vol.Required(key): SelectSelector(
                SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
            )
        }
    )


async def _time_zone_selector(hass) -> SelectSelector:
    zones = await hass.async_add_executor_job(available_timezones)
    return SelectSelector(
        SelectSelectorConfig(
            options=sorted(zones), mode=SelectSelectorMode.DROPDOWN, sort=False
        )
    )


async def _settings_schema(hass, language: str, time_zone: str) -> dict:
    """Language and time zone fields, shared by setup and Configure."""
    return {
        vol.Required(CONF_LANGUAGE, default=language): _language_selector(),
        vol.Required(CONF_TIME_ZONE, default=time_zone): await _time_zone_selector(
            hass
        ),
    }


def _ezan_prayers_selector(language: str) -> SelectSelector:
    options = [
        SelectOptionDict(value=key, label=i18n.name(key, language))
        for key in DAILY_PRAYERS
    ]
    return SelectSelector(
        SelectSelectorConfig(
            options=options, multiple=True, mode=SelectSelectorMode.LIST
        )
    )


class DiyanetConfigFlow(ConfigFlow, domain=DOMAIN):
    """Pick country, state and city from Diyanet's location list."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._places: dict[str, str] = {}
        self._data: dict[str, str] = {}

    @property
    def _client(self) -> DiyanetClient:
        return DiyanetClient(async_get_clientsession(self.hass))

    async def _async_step_select(
        self,
        step_id: str,
        id_key: str,
        name_key: str,
        user_input: dict[str, Any] | None,
        load,
        extra: dict | None = None,
    ) -> ConfigFlowResult | None:
        """Show a place dropdown; return None once a valid choice was made."""
        errors: dict[str, str] = {}
        if user_input is not None and user_input[id_key] in self._places:
            self._data[id_key] = user_input[id_key]
            self._data[name_key] = self._places[user_input[id_key]]
            return None
        try:
            self._places = await load()
        except DiyanetConnectionError:
            errors["base"] = "cannot_connect"
            self._places = {}
        if not self._places and not errors:
            return self.async_abort(reason="no_places")
        schema = _select_schema(id_key, self._places)
        if extra:
            schema = schema.extend(extra)
        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the country."""
        if result := await self._async_step_select(
            "user",
            CONF_COUNTRY_ID,
            CONF_COUNTRY_NAME,
            user_input,
            self._client.async_get_countries,
        ):
            return result
        return await self.async_step_state()

    async def async_step_state(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the state (province in Turkey)."""
        if result := await self._async_step_select(
            "state",
            CONF_STATE_ID,
            CONF_STATE_NAME,
            user_input,
            lambda: self._client.async_get_states(self._data[CONF_COUNTRY_ID]),
        ):
            return result
        return await self.async_step_city()

    async def async_step_city(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the city (district in Turkey) and create the entry."""
        if result := await self._async_step_select(
            "city",
            CONF_CITY_ID,
            CONF_CITY_NAME,
            user_input,
            lambda: self._client.async_get_cities(self._data[CONF_STATE_ID]),
            await _settings_schema(self.hass, LANGUAGE_AUTO, self.hass.config.time_zone),
        ):
            return result
        await self.async_set_unique_id(self._data[CONF_CITY_ID])
        self._abort_if_unique_id_configured()
        city, state = self._data[CONF_CITY_NAME], self._data[CONF_STATE_NAME]
        title = city if city == state else f"{city}, {state}"
        user_input = user_input or {}
        return self.async_create_entry(
            title=title,
            data=self._data,
            options={
                CONF_LANGUAGE: user_input.get(CONF_LANGUAGE, LANGUAGE_AUTO),
                CONF_TIME_ZONE: user_input.get(
                    CONF_TIME_ZONE, self.hass.config.time_zone
                ),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> DiyanetOptionsFlow:
        """Return the options flow."""
        return DiyanetOptionsFlow()


class DiyanetOptionsFlow(OptionsFlow):
    """Change language, time zone and which prayers trigger the ezan."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the language, time zone and ezan prayers."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        options = self.config_entry.options
        language = options.get(CONF_LANGUAGE, LANGUAGE_AUTO)
        schema = await _settings_schema(
            self.hass,
            language,
            options.get(CONF_TIME_ZONE, self.hass.config.time_zone),
        )
        schema[
            vol.Optional(
                CONF_EZAN_PRAYERS,
                default=options.get(CONF_EZAN_PRAYERS, list(DAILY_PRAYERS)),
            )
        ] = _ezan_prayers_selector(
            i18n.resolve_language(language, self.hass.config.language)
        )
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))
