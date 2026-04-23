from __future__ import annotations

import calendar as _calendar
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import List

from dateutil.rrule import rrulestr

from .config import CalendarConfig, EventDef


@dataclass(frozen=True)
class EventOccurrence:
    event: EventDef
    start: datetime
    end: datetime


def _parse_hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def occurrences_for_month(
    cfg: CalendarConfig, year: int, month: int
) -> List[EventOccurrence]:
    """Return all event occurrences whose start falls within [year-month]."""
    _, last_day = _calendar.monthrange(year, month)
    month_start = datetime(year, month, 1, tzinfo=cfg.tz)
    month_end = datetime(year, month, last_day, 23, 59, 59, tzinfo=cfg.tz)
    # rrule needs a DTSTART to anchor. Use one year before the month so
    # monthly rrules (e.g. 3rd Friday) land correctly in the target month.
    anchor = month_start - timedelta(days=400)

    results: List[EventOccurrence] = []
    for evt in cfg.events:
        start_t = _parse_hhmm(evt.start_time)
        end_t = _parse_hhmm(evt.end_time)
        dtstart = datetime.combine(anchor.date(), start_t, tzinfo=cfg.tz)
        rule = rrulestr(evt.rrule, dtstart=dtstart)
        for occ in rule.between(month_start, month_end, inc=True):
            start = occ
            end = datetime.combine(occ.date(), end_t, tzinfo=cfg.tz)
            results.append(EventOccurrence(event=evt, start=start, end=end))

    results.sort(key=lambda o: o.start)
    return results
