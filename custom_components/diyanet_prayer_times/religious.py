"""Ramadan and religious days derived from Diyanet's Hijri dates.

The data source has no calendar endpoint, but every day carries Diyanet's
Hijri date. Everything here is derived from that; dates beyond the ~32-day
window are estimated from the mean lunar month length.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .api import DayTimes

RAMADAN = 9
SHAWWAL = 10
RAJAB = 7
MEAN_LUNAR_MONTH = 29.530589  # days

# (Hijri month, Hijri day) -> key. Kandil nights are listed on the day whose
# evening starts the holy night, as in Diyanet's calendar.
FIXED_DAYS: dict[tuple[int, int], str] = {
    (1, 1): "hijri_new_year",
    (1, 10): "ashura",
    (3, 11): "mawlid",
    (7, 26): "miraj",
    (8, 14): "barat",
    (9, 1): "ramadan_start",
    (9, 26): "qadr",
    (12, 9): "eid_al_adha_eve",
}
# Multi-day feasts: (month, first day, number of days) -> key.
FEASTS: dict[tuple[int, int, int], str] = {
    (10, 1, 3): "eid_al_fitr",
    (12, 10, 4): "eid_al_adha",
}


@dataclass(frozen=True, slots=True)
class RamadanInfo:
    """Ramadan status for today."""

    active: bool
    day: int | None
    first_day: date | None
    last_day: date | None
    next_start: date
    next_start_estimated: bool


@dataclass(frozen=True, slots=True)
class ReligiousDay:
    """A religious day; `number` is the feast day (e.g. 2nd day of Eid)."""

    key: str
    date: date
    number: int | None = None


def _index(days: list[DayTimes], today: date) -> int | None:
    for i, day in enumerate(days):
        if day.date == today:
            return i
    return None


def _find(days: list[DayTimes], month: int, mday: int, after: date) -> date | None:
    for day in days:
        if day.date > after and day.hijri_date and day.hijri_date[:2] == (mday, month):
            return day.date
    return None


def _estimate_start(today: DayTimes, months_ahead: int) -> date:
    """Estimate day 1 of the month `months_ahead` Hijri months from today."""
    mday = today.hijri_date[0]
    return today.date + timedelta(
        days=round(months_ahead * MEAN_LUNAR_MONTH - (mday - 1))
    )


def ramadan_info(days: list[DayTimes], today: date) -> RamadanInfo | None:
    """Return Ramadan status, or None if today's Hijri date is unknown."""
    if (i := _index(days, today)) is None or days[i].hijri_date is None:
        return None
    current = days[i]
    mday, month, _ = current.hijri_date
    active = month == RAMADAN

    first_day = last_day = None
    if active:
        first_day = today - timedelta(days=mday - 1)
        if shawwal := _find(days, SHAWWAL, 1, today):
            last_day = shawwal - timedelta(days=1)

    if not active and (start := _find(days, RAMADAN, 1, today - timedelta(days=1))):
        next_start, estimated = start, False
    else:
        months_ahead = (RAMADAN - month) % 12 or 12
        next_start, estimated = _estimate_start(current, months_ahead), True

    return RamadanInfo(
        active=active,
        day=mday if active else None,
        first_day=first_day,
        last_day=last_day,
        next_start=next_start,
        next_start_estimated=estimated,
    )


def _religious_day_at(days: list[DayTimes], i: int) -> ReligiousDay | None:
    day = days[i]
    if day.hijri_date is None:
        return None
    mday, month, _ = day.hijri_date
    nxt = days[i + 1].hijri_date if i + 1 < len(days) else None

    if key := FIXED_DAYS.get((month, mday)):
        return ReligiousDay(key, day.date)
    for (f_month, f_first, length), key in FEASTS.items():
        if month == f_month and f_first <= mday < f_first + length:
            return ReligiousDay(key, day.date, mday - f_first + 1)
    # Eve of Eid al-Fitr: last day of Ramadan (29th or 30th).
    if month == RAMADAN and nxt and nxt[:2] == (1, SHAWWAL):
        return ReligiousDay("eid_al_fitr_eve", day.date)
    # Regaib: the Thursday evening before the first Friday of Rajab.
    if day.date.weekday() == 3 and nxt and nxt[1] == RAJAB and nxt[0] <= 7:
        return ReligiousDay("regaib", day.date)
    return None


def religious_day(days: list[DayTimes], today: date) -> ReligiousDay | None:
    """Return today's religious day, if any."""
    if (i := _index(days, today)) is None:
        return None
    return _religious_day_at(days, i)


def next_religious_day(days: list[DayTimes], today: date) -> ReligiousDay | None:
    """Return the next religious day after today within the data window."""
    if (i := _index(days, today)) is None:
        return None
    for j in range(i + 1, len(days)):
        if found := _religious_day_at(days, j):
            return found
    return None
