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
    coordinator = entry.runtime_data
    async_add_entities(
        [EzanBinarySensor(coordinator), RamadanBinarySensor(coordinator)]
    )


class EzanBinarySensor(DiyanetEntity, BinarySensorEntity):
    """On for one minute at each selected prayer time, while enabled.

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
        """Return True during the minute after a selected prayer time."""
        return self.coordinator.ezan_prayer() is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return which prayer's ezan this is."""
        return {"prayer": self.coordinator.ezan_prayer()}


class RamadanBinarySensor(DiyanetEntity, BinarySensorEntity):
    """On during Ramadan, per Diyanet's Hijri calendar."""

    _attr_icon = "mdi:star-crescent"

    def __init__(self, coordinator: DiyanetCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, "binary_sensor", "ramadan", "ramadan")

    @property
    def is_on(self) -> bool | None:
        """Return True during Ramadan."""
        if (info := self.coordinator.ramadan()) is None:
            return None
        return info.active

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the day of Ramadan and its first and last day."""
        info = self.coordinator.ramadan()
        if info is None or not info.active:
            return {"day": None, "first_day": None, "last_day": None}
        return {
            "day": info.day,
            "first_day": info.first_day.isoformat(),
            "last_day": info.last_day.isoformat() if info.last_day else None,
        }
