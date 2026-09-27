"""Switch that enables or disables the ezan binary sensor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .coordinator import DiyanetConfigEntry, DiyanetCoordinator
from .entity import DiyanetEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DiyanetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switch."""
    async_add_entities([EzanSwitch(entry.runtime_data)])


class EzanSwitch(DiyanetEntity, SwitchEntity, RestoreEntity):
    """When off, the ezan binary sensor never turns on."""

    _attr_icon = "mdi:bullhorn"

    def __init__(self, coordinator: DiyanetCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, "switch", "ezan_active", "ezan_active")

    async def async_added_to_hass(self) -> None:
        """Restore the last position (default: on)."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self.coordinator.ezan_enabled = last.state != STATE_OFF
            self.coordinator.async_update_listeners()

    @property
    def is_on(self) -> bool:
        """Return whether the ezan trigger is enabled."""
        return self.coordinator.ezan_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the ezan trigger."""
        self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the ezan trigger."""
        self._set(False)

    def _set(self, enabled: bool) -> None:
        self.coordinator.ezan_enabled = enabled
        # Also refreshes the binary sensor.
        self.coordinator.async_update_listeners()
