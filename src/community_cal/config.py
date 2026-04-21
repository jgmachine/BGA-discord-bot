from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List
from zoneinfo import ZoneInfo

import yaml


@dataclass(frozen=True)
class EventDef:
    name: str
    venue: str
    rrule: str
    start_time: str
    end_time: str
    color: str


@dataclass(frozen=True)
class CalendarConfig:
    tz: ZoneInfo
    events: List[EventDef]


def load_config(path: Path) -> CalendarConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)

    tz = ZoneInfo(raw["timezone"])
    events = [
        EventDef(
            name=e["name"],
            venue=e["venue"],
            rrule=e["rrule"],
            start_time=e["start_time"],
            end_time=e["end_time"],
            color=e["color"],
        )
        for e in raw["events"]
    ]
    return CalendarConfig(tz=tz, events=events)


DEFAULT_CONFIG_PATH = Path(__file__).parent / "events.yaml"
