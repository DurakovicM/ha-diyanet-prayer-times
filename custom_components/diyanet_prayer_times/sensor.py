"""Sensors for Diyanet Prayer Times."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PRAYERS
from .coordinator import DiyanetConfigEntry, DiyanetCoordinator
from .hijri import format_hijri


def _clock(value: datetime | None) -> str | None:
    """Local wall-clock time at the city, as published (e.g. '05:23')."""
    return value.strftime("%H:%M") if value else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DiyanetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        PrayerTimeSensor(coordinator, prayer) for prayer in PRAYERS
    ]
    entities += [NextPrayerSensor(coordinator), HijriDateSensor(coordinator)]
    async_add_entities(entities)


class DiyanetEntity(CoordinatorEntity[DiyanetCoordinator], SensorEntity):
    """Base entity attached to one service device per city."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DiyanetCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Diyanet İşleri Başkanlığı",
            entry_type=DeviceEntryType.SERVICE,
        )


class PrayerTimeSensor(DiyanetEntity):
    """Today's time for one prayer."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: DiyanetCoordinator, prayer: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, prayer)
        self._prayer = prayer

    @property
    def native_value(self) -> datetime | None:
        """Return today's prayer time."""
        if (today := self.coordinator.today()) is None:
            return None
        return today.times[self._prayer]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the plain published time for dashboards."""
        return {"time": _clock(self.native_value)}


class NextPrayerSensor(DiyanetEntity):
    """The next upcoming prayer."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: DiyanetCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "next_prayer")

    @property
    def native_value(self) -> datetime | None:
        """Return the time of the next prayer."""
        if (upcoming := self.coordinator.next_prayer()) is None:
            return None
        return upcoming[1]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return which prayer is next and its plain time."""
        if (upcoming := self.coordinator.next_prayer()) is None:
            return {"prayer": None, "time": None}
        return {"prayer": upcoming[0], "time": _clock(upcoming[1])}


class HijriDateSensor(DiyanetEntity):
    """Today's Hijri date, with moon phase and qibla time."""

    def __init__(self, coordinator: DiyanetCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "hijri_date")

    @property
    def native_value(self) -> str | None:
        """Return the Hijri date in Home Assistant's language."""
        if (today := self.coordinator.today()) is None:
            return None
        if today.hijri_date is None:
            return today.hijri
        return format_hijri(*today.hijri_date, self.hass.config.language)

    @property
    def entity_picture(self) -> str | None:
        """Return the moon phase image."""
        if (today := self.coordinator.today()) is None:
            return None
        return today.moon_url

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return qibla time and the Gregorian date."""
        if (today := self.coordinator.today()) is None:
            return {}
        return {"qibla_time": today.qibla_time, "date": today.date.isoformat()}
