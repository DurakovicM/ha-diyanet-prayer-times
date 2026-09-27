"""Tests for Ramadan and religious days derived from Hijri dates."""

from __future__ import annotations

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from custom_components.diyanet_prayer_times.api import DayTimes, parse_times
from custom_components.diyanet_prayer_times.religious import (
    next_religious_day,
    ramadan_info,
    religious_day,
)


def make_days(
    start: date, hijri: tuple[int, int, int], count: int = 32, lengths=None
) -> list[DayTimes]:
    """Consecutive days; Hijri months are 30 days unless given in `lengths`."""
    lengths = lengths or {}
    mday, month, year = hijri
    days = []
    for offset in range(count):
        days.append(
            DayTimes(
                date=start + timedelta(days=offset),
                times={},
                hijri=None,
                hijri_date=(mday, month, year),
                moon_url=None,
                qibla_time=None,
            )
        )
        mday += 1
        if mday > lengths.get(month, 30):
            mday, month = 1, month % 12 + 1
            year += month == 1
    return days


def test_estimates_next_ramadan_from_real_data(raw_times) -> None:
    """Outside the window the start is estimated (15 Rebiulahir 1448 today)."""
    days = parse_times(raw_times, ZoneInfo("Europe/Istanbul"))
    info = ramadan_info(days, date(2026, 9, 26))

    assert info.active is False
    assert info.day is None
    assert info.next_start_estimated is True
    # 1 Ramadan 1448 is expected around 8 February 2027.
    assert abs((info.next_start - date(2027, 2, 8)).days) <= 2


def test_exact_start_when_in_window() -> None:
    """Once 1 Ramadan is in the data, the start date is exact."""
    days = make_days(date(2027, 1, 20), (11, 8, 1448))  # 11 Şaban
    info = ramadan_info(days, date(2027, 1, 20))

    assert info.active is False
    assert info.next_start == date(2027, 2, 9)
    assert info.next_start_estimated is False


def test_during_ramadan() -> None:
    """Day number, first and last day (29-day Ramadan) are known."""
    days = make_days(date(2027, 2, 20), (13, 9, 1448), lengths={9: 29})
    info = ramadan_info(days, date(2027, 2, 20))

    assert info.active is True
    assert info.day == 13
    assert info.first_day == date(2027, 2, 8)
    assert info.last_day == date(2027, 3, 8)
    # Next Ramadan is about a lunar year later.
    assert info.next_start_estimated is True
    assert 350 <= (info.next_start - info.first_day).days <= 357


def test_ramadan_religious_days() -> None:
    """Kadir, Eid eve and the Eid days are recognised."""
    days = make_days(date(2027, 2, 20), (13, 9, 1448), lengths={9: 29})

    assert religious_day(days, date(2027, 2, 20)) is None
    assert religious_day(days, date(2027, 3, 5)).key == "qadr"  # 26 Ramadan
    assert religious_day(days, date(2027, 3, 8)).key == "eid_al_fitr_eve"
    eid1 = religious_day(days, date(2027, 3, 9))
    assert (eid1.key, eid1.number) == ("eid_al_fitr", 1)
    eid3 = religious_day(days, date(2027, 3, 11))
    assert (eid3.key, eid3.number) == ("eid_al_fitr", 3)
    assert religious_day(days, date(2027, 3, 12)) is None


def test_next_religious_day() -> None:
    """The next religious day within the window is found."""
    days = make_days(date(2027, 2, 20), (13, 9, 1448), lengths={9: 29})
    upcoming = next_religious_day(days, date(2027, 2, 20))
    assert (upcoming.key, upcoming.date) == ("qadr", date(2027, 3, 5))


def test_regaib_is_thursday_before_first_friday_of_rajab() -> None:
    """Regaib falls on the Thursday whose next day is a Friday in 1-7 Rajab."""
    # 2027-12-01 is a Wednesday; start on 28 Jumada al-Akhirah.
    days = make_days(date(2027, 12, 1), (28, 6, 1449))
    found = [
        religious_day(days, d.date)
        for d in days
        if religious_day(days, d.date) is not None
    ]
    regaib = [r for r in found if r.key == "regaib"]
    assert len(regaib) == 1
    assert regaib[0].date.weekday() == 3
    friday = next(d for d in days if d.date == regaib[0].date + timedelta(days=1))
    assert friday.hijri_date[1] == 7 and friday.hijri_date[0] <= 7


def test_unknown_hijri_date() -> None:
    """Without a Hijri date there is no Ramadan info."""
    days = [
        DayTimes(date(2027, 1, 1), {}, None, None, None, None),
    ]
    assert ramadan_info(days, date(2027, 1, 1)) is None
    assert religious_day(days, date(2027, 1, 1)) is None
