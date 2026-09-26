"""Binary sensor that is on while the ezan should play."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DiyanetConfigEntry, DiyanetCoordinator
from .entity import DiyanetEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DiyanetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor."""
    async_add_entities([EzanBinarySensor(entry.runtime_data)])


class EzanBinarySensor(DiyanetEntity, BinarySensorEntity):
    """On for one minute at each of the five prayer times.

    Uses the motion device class so voice assistants such as Alexa can
    start a routine from it.
    """

    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_icon = "mdi:mosque"

    def __init__(self, coordinator: DiyanetCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, "binary_sensor", "ezan", "ezan")

    @property
    def is_on(self) -> bool:
        """Return True during the minute after a prayer time."""
        return self.coordinator.active_prayer() is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return which prayer's ezan this is."""
        return {"prayer": self.coordinator.active_prayer()}
