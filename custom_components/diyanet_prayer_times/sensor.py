"""Sensors for Diyanet Prayer Times."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN, PRAYERS
from .coordinator import DiyanetConfigEntry, DiyanetCoordinator
from . import i18n


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
    entities: list[SensorEntity] = []
    for prayer in PRAYERS:
        entities += [
            PrayerClockSensor(coordinator, prayer),
            PrayerTimestampSensor(coordinator, prayer),
        ]
    entities += [
        NextPrayerSensor(coordinator),
        NextPrayerTimestampSensor(coordinator),
        HijriDateSensor(coordinator),
    ]
    async_add_entities(entities)


class DiyanetEntity(CoordinatorEntity[DiyanetCoordinator], SensorEntity):
    """Base entity attached to one service device per city.

    Names come from the integration's own language setting rather than
    Home Assistant's, so they are set directly instead of via translations.
    Entity IDs are language-independent: sensor.<device>_<object_id>.
    """

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: DiyanetCoordinator, key: str, object_id: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.unique_id}_{object_id}"
        # Same prefix Home Assistant derives from the device name.
        self.entity_id = f"sensor.{slugify(entry.title)}_{object_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Diyanet İşleri Başkanlığı",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def name(self) -> str:
        """Return the name in the integration's language."""
        return i18n.name(self._key, self.coordinator.language)


class PrayerTimestampSensor(DiyanetEntity):
    """Today's time for one prayer as a timestamp, for automations."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: DiyanetCoordinator, prayer: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, prayer, prayer)

    @property
    def name(self) -> str:
        """Return e.g. 'Sunset timestamp'."""
        language = self.coordinator.language
        return f"{i18n.name(self._key, language)} {i18n.name('timestamp', language)}"

    @property
    def native_value(self) -> datetime | None:
        """Return today's prayer time."""
        if (today := self.coordinator.today()) is None:
            return None
        return today.times[self._key]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the plain published time."""
        return {"time": _clock(self.native_value)}


class PrayerClockSensor(DiyanetEntity):
    """Today's time for one prayer as plain text, e.g. '05:23'."""

    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: DiyanetCoordinator, prayer: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, prayer, f"{prayer}_time")

    @property
    def native_value(self) -> str | None:
        """Return today's published time."""
        if (today := self.coordinator.today()) is None:
            return None
        return _clock(today.times[self._key])


class NextPrayerTimestampSensor(DiyanetEntity):
    """The next upcoming prayer as a timestamp, for automations."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: DiyanetCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "next_prayer", "next_prayer")

    @property
    def name(self) -> str:
        """Return e.g. 'Next prayer timestamp'."""
        language = self.coordinator.language
        return f"{i18n.name(self._key, language)} {i18n.name('timestamp', language)}"

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


class NextPrayerSensor(DiyanetEntity):
    """The next upcoming prayer as text, e.g. 'Sunset 19:03'."""

    _attr_icon = "mdi:mosque"

    def __init__(self, coordinator: DiyanetCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "next_prayer", "next_prayer_time")

    @property
    def native_value(self) -> str | None:
        """Return the next prayer's name and time."""
        if (upcoming := self.coordinator.next_prayer()) is None:
            return None
        prayer, when = upcoming
        return f"{i18n.name(prayer, self.coordinator.language)} {_clock(when)}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the prayer key for automations."""
        upcoming = self.coordinator.next_prayer()
        return {"prayer": upcoming[0] if upcoming else None}


class HijriDateSensor(DiyanetEntity):
    """Today's Hijri date, with moon phase and qibla time."""

    _attr_icon = "mdi:calendar-star"

    def __init__(self, coordinator: DiyanetCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "hijri_date", "hijri_date")

    @property
    def native_value(self) -> str | None:
        """Return the Hijri date in the integration's language."""
        if (today := self.coordinator.today()) is None:
            return None
        if today.hijri_date is None:
            return today.hijri
        return i18n.format_hijri(*today.hijri_date, self.coordinator.language)

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
