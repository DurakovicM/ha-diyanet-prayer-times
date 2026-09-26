"""Config flow for Diyanet Prayer Times."""

from __future__ import annotations

from typing import Any

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

from .api import DiyanetClient, DiyanetConnectionError
from .const import (
    CONF_CITY_ID,
    CONF_CITY_NAME,
    CONF_COUNTRY_ID,
    CONF_COUNTRY_NAME,
    CONF_LANGUAGE,
    CONF_STATE_ID,
    CONF_STATE_NAME,
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
            {vol.Required(CONF_LANGUAGE, default=LANGUAGE_AUTO): _language_selector()},
        ):
            return result
        await self.async_set_unique_id(self._data[CONF_CITY_ID])
        self._abort_if_unique_id_configured()
        city, state = self._data[CONF_CITY_NAME], self._data[CONF_STATE_NAME]
        title = city if city == state else f"{city}, {state}"
        language = (user_input or {}).get(CONF_LANGUAGE, LANGUAGE_AUTO)
        return self.async_create_entry(
            title=title, data=self._data, options={CONF_LANGUAGE: language}
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> DiyanetOptionsFlow:
        """Return the options flow."""
        return DiyanetOptionsFlow()


class DiyanetOptionsFlow(OptionsFlow):
    """Change the integration's display language."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the language."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_LANGUAGE, LANGUAGE_AUTO)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required(CONF_LANGUAGE, default=current): _language_selector()}
            ),
        )
