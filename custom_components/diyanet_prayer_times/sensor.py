"""Sensors for Diyanet Prayer Times."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import PRAYERS
from .coordinator import DiyanetConfigEntry, DiyanetCoordinator
from .entity import DiyanetEntity
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
        DaysUntilRamadanSensor(coordinator),
        ReligiousDaySensor(coordinator),
    ]
    async_add_entities(entities)


class PrayerTimestampSensor(DiyanetEntity, SensorEntity):
    """Today's time for one prayer as a timestamp, for automations."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: DiyanetCoordinator, prayer: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "sensor", prayer, prayer)

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


class PrayerClockSensor(DiyanetEntity, SensorEntity):
    """Today's time for one prayer as plain text, e.g. '05:23'."""

    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: DiyanetCoordinator, prayer: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "sensor", prayer, f"{prayer}_time")

    @property
    def native_value(self) -> str | None:
        """Return today's published time."""
        if (today := self.coordinator.today()) is None:
            return None
        return _clock(today.times[self._key])


class NextPrayerTimestampSensor(DiyanetEntity, SensorEntity):
    """The next upcoming prayer as a timestamp, for automations."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: DiyanetCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "sensor", "next_prayer", "next_prayer")

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


class NextPrayerSensor(DiyanetEntity, SensorEntity):
    """The next upcoming prayer as text, e.g. 'Sunset 19:03'."""

    _attr_icon = "mdi:mosque"

    def __init__(self, coordinator: DiyanetCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "sensor", "next_prayer", "next_prayer_time")

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


class HijriDateSensor(DiyanetEntity, SensorEntity):
    """Today's Hijri date, with moon phase and qibla time."""

    _attr_icon = "mdi:calendar-star"

    def __init__(self, coordinator: DiyanetCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "sensor", "hijri_date", "hijri_date")

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


class DaysUntilRamadanSensor(DiyanetEntity, SensorEntity):
    """Days until the next Ramadan (0 during Ramadan)."""

    _attr_icon = "mdi:calendar-clock"
    _attr_native_unit_of_measurement = UnitOfTime.DAYS

    def __init__(self, coordinator: DiyanetCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, "sensor", "days_until_ramadan", "days_until_ramadan"
        )

    @property
    def native_value(self) -> int | None:
        """Return the number of days until Ramadan starts."""
        if (info := self.coordinator.ramadan()) is None:
            return None
        if info.active:
            return 0
        return (info.next_start - self.coordinator.today().date).days

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the (possibly estimated) start date."""
        if (info := self.coordinator.ramadan()) is None:
            return {}
        return {
            "start_date": info.next_start.isoformat(),
            "estimated": info.next_start_estimated,
        }


class ReligiousDaySensor(DiyanetEntity, SensorEntity):
    """Today's religious day (Kandil, Eid, ...) per Diyanet's Hijri calendar."""

    _attr_icon = "mdi:star-four-points"

    def __init__(self, coordinator: DiyanetCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "sensor", "religious_day", "religious_day")

    def _name(self, day) -> str:
        return i18n.religious_day_name(
            day.key if day else "none",
            day.number if day else None,
            self.coordinator.language,
        )

    @property
    def native_value(self) -> str | None:
        """Return today's religious day, or 'None' in the chosen language."""
        if self.coordinator.today() is None:
            return None
        today, _ = self.coordinator.religious_days()
        return self._name(today)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return stable keys for automations and the next religious day."""
        today, upcoming = self.coordinator.religious_days()
        return {
            "key": today.key if today else "none",
            "next": self._name(upcoming) if upcoming else None,
            "next_key": upcoming.key if upcoming else None,
            "next_date": upcoming.date.isoformat() if upcoming else None,
        }
