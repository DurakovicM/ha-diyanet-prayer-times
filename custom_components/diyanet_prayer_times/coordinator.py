"""Data coordinator for Diyanet Prayer Times."""

from __future__ import annotations

from datetime import datetime, time, timedelta, tzinfo
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import DayTimes, DiyanetClient, DiyanetConnectionError, parse_times
from .const import (
    CONF_CITY_ID,
    CONF_LANGUAGE,
    CONF_TIME_ZONE,
    DOMAIN,
    LANGUAGE_AUTO,
    UPDATE_INTERVAL,
)
from .i18n import base_language

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1

# Prayers considered for "next prayer" and the ezan (sunrise is not a prayer).
NEXT_PRAYER_KEYS = ("imsak", "dhuhr", "asr", "maghrib", "isha")
# How long the ezan binary sensor stays on after a prayer time.
EZAN_DURATION = timedelta(minutes=1)

type DiyanetConfigEntry = ConfigEntry[DiyanetCoordinator]


class DiyanetCoordinator(DataUpdateCoordinator[list[DayTimes]]):
    """Fetch official times, persist them, and tick sensors at prayer times."""

    config_entry: DiyanetConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: DiyanetConfigEntry, client: DiyanetClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self.city_id: str = entry.data[CONF_CITY_ID]
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{self.city_id}"
        )
        self._cached: list[DayTimes] = []
        self._unsub_tick: CALLBACK_TYPE | None = None

    async def _async_setup(self) -> None:
        """Load the persisted times so sensors work while offline."""
        if stored := await self._store.async_load():
            self._cached = parse_times(stored.get("times", []), self.time_zone)

    async def _async_update_data(self) -> list[DayTimes]:
        try:
            raw = await self.client.async_get_times(self.city_id)
            days = parse_times(raw, self.time_zone)
            if not days:
                raise DiyanetConnectionError("Response contained no usable days")
        except DiyanetConnectionError as err:
            if self.day_for(dt_util.utcnow(), self._cached) is not None:
                _LOGGER.warning("Using cached prayer times, update failed: %s", err)
                return self._cached
            raise UpdateFailed(f"No prayer times available: {err}") from err

        if len(days) < 2:
            _LOGGER.warning(
                "Diyanet source returned only %s day(s); it may be going away",
                len(days),
            )
        await self._store.async_save({"times": raw})
        self._cached = days
        return days

    @property
    def time_zone(self) -> tzinfo:
        """Time zone of the location: the entry's choice, or Home Assistant's."""
        name = self.config_entry.options.get(CONF_TIME_ZONE)
        if name and (tz := dt_util.get_time_zone(name)):
            return tz
        return dt_util.get_default_time_zone()

    @property
    def language(self) -> str:
        """Display language: the entry's choice, or Home Assistant's."""
        chosen = self.config_entry.options.get(CONF_LANGUAGE, LANGUAGE_AUTO)
        if chosen == LANGUAGE_AUTO:
            return base_language(self.hass.config.language)
        return base_language(chosen)

    @staticmethod
    def day_for(now: datetime, days: list[DayTimes]) -> DayTimes | None:
        """Return the entry for the current date at the city's location."""
        for day in days:
            if now.astimezone(day.times["imsak"].tzinfo).date() == day.date:
                return day
        return None

    def today(self, now: datetime | None = None) -> DayTimes | None:
        """Return today's times at the city's location."""
        return self.day_for(now or dt_util.utcnow(), self.data or [])

    def next_prayer(self, now: datetime | None = None) -> tuple[str, datetime] | None:
        """Return (prayer key, time) of the next upcoming prayer."""
        now = now or dt_util.utcnow()
        for day in self.data or []:
            for key in NEXT_PRAYER_KEYS:
                if day.times[key] > now:
                    return key, day.times[key]
        return None

    def active_prayer(self, now: datetime | None = None) -> str | None:
        """Return the prayer whose ezan window contains now, if any."""
        now = now or dt_util.utcnow()
        for day in self.data or []:
            for key in NEXT_PRAYER_KEYS:
                if day.times[key] <= now < day.times[key] + EZAN_DURATION:
                    return key
        return None

    def _next_tick(self, now: datetime) -> datetime | None:
        """Next moment a sensor value changes: a prayer or the city's midnight."""
        candidates = [
            t for day in self.data or [] for t in day.times.values() if t > now
        ]
        candidates += [
            end
            for day in self.data or []
            for key in NEXT_PRAYER_KEYS
            if (end := day.times[key] + EZAN_DURATION) > now
        ]
        if (today := self.today(now)) is not None:
            tz = today.times["imsak"].tzinfo
            candidates.append(
                datetime.combine(today.date + timedelta(days=1), time(0, 0, 1), tz)
            )
        return min(candidates, default=None)

    @callback
    def _async_schedule_tick(self) -> None:
        if self._unsub_tick:
            self._unsub_tick()
            self._unsub_tick = None
        if (when := self._next_tick(dt_util.utcnow())) is not None:
            self._unsub_tick = async_track_point_in_time(
                self.hass, self._async_handle_tick, when
            )

    @callback
    def _async_handle_tick(self, _now: datetime) -> None:
        self._unsub_tick = None
        self.async_update_listeners()

    @callback
    def async_update_listeners(self) -> None:
        """Notify listeners and reschedule the next tick for the current data."""
        super().async_update_listeners()
        self._async_schedule_tick()

    async def async_shutdown(self) -> None:
        """Cancel the scheduled tick."""
        if self._unsub_tick:
            self._unsub_tick()
            self._unsub_tick = None
        await super().async_shutdown()
