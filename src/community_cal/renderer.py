from __future__ import annotations

import calendar as _calendar
import io
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from .config import CalendarConfig
from .events import EventOccurrence, occurrences_for_month

WIDTH = 1600
HEIGHT = 1200
MARGIN = 40
HEADER_H = 120
WEEKDAY_H = 50
LEGEND_H = 90

BG = (24, 26, 30)
FG = (232, 233, 235)
MUTED = (140, 145, 155)
GRID = (58, 62, 70)
CELL_BG = (34, 37, 43)
OTHER_MONTH_BG = (28, 30, 35)
TODAY_RING = (255, 214, 102)


_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        if not Path(path).exists():
            continue
        if bold and "Bold" not in path and "Arial" not in path and "Helvetica" not in path:
            continue
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex_to_rgb(s: str) -> Tuple[int, int, int]:
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def render_month(
    cfg: CalendarConfig,
    year: int,
    month: int,
    today: Optional[date] = None,
) -> bytes:
    occs = occurrences_for_month(cfg, year, month)
    by_day: Dict[int, List[EventOccurrence]] = {}
    for o in occs:
        by_day.setdefault(o.start.day, []).append(o)

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    title_font = _load_font(54, bold=True)
    weekday_font = _load_font(24, bold=True)
    day_font = _load_font(28, bold=True)
    event_font = _load_font(20, bold=False)
    legend_font = _load_font(22, bold=False)

    month_name = _calendar.month_name[month]
    title = f"{month_name} {year}"
    draw.text((MARGIN, MARGIN), title, fill=FG, font=title_font)
    draw.text(
        (MARGIN, MARGIN + 70),
        "Redding community events",
        fill=MUTED,
        font=legend_font,
    )

    grid_top = MARGIN + HEADER_H
    grid_left = MARGIN
    grid_right = WIDTH - MARGIN
    grid_bottom = HEIGHT - MARGIN - LEGEND_H

    week_rows = _calendar.monthcalendar(year, month)
    n_rows = len(week_rows)
    cell_w = (grid_right - grid_left) // 7
    cell_h = (grid_bottom - grid_top - WEEKDAY_H) // n_rows

    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i, name in enumerate(weekday_names):
        x = grid_left + i * cell_w
        draw.rectangle(
            [x, grid_top, x + cell_w, grid_top + WEEKDAY_H],
            fill=BG,
        )
        tw = draw.textlength(name, font=weekday_font)
        draw.text(
            (x + (cell_w - tw) // 2, grid_top + 12),
            name,
            fill=MUTED,
            font=weekday_font,
        )

    cells_top = grid_top + WEEKDAY_H
    for row_idx, week in enumerate(week_rows):
        for col_idx, day in enumerate(week):
            x0 = grid_left + col_idx * cell_w
            y0 = cells_top + row_idx * cell_h
            x1 = x0 + cell_w
            y1 = y0 + cell_h

            bg = CELL_BG if day != 0 else OTHER_MONTH_BG
            draw.rectangle([x0, y0, x1, y1], fill=bg, outline=GRID, width=1)

            if day == 0:
                continue

            if today is not None and today.year == year and today.month == month and today.day == day:
                draw.rectangle([x0, y0, x1, y1], outline=TODAY_RING, width=3)

            draw.text((x0 + 10, y0 + 6), str(day), fill=FG, font=day_font)

            day_events = by_day.get(day, [])
            pill_y = y0 + 44
            for occ in day_events:
                color = _hex_to_rgb(occ.event.color)
                pill_x0 = x0 + 8
                pill_x1 = x1 - 8
                pill_y0 = pill_y
                pill_y1 = pill_y + 32
                if pill_y1 > y1 - 6:
                    break
                draw.rectangle([pill_x0, pill_y0, pill_x1, pill_y1], fill=color)
                label = f"{occ.start.strftime('%-I%p').lower()} {occ.event.short_label}"
                max_w = pill_x1 - pill_x0 - 12
                while draw.textlength(label, font=event_font) > max_w and len(label) > 3:
                    label = label[:-2] + "…"
                draw.text((pill_x0 + 8, pill_y0 + 4), label, fill=(255, 255, 255), font=event_font)
                pill_y += 38

    legend_y = HEIGHT - MARGIN - LEGEND_H + 20
    lx = MARGIN
    for evt in cfg.events:
        color = _hex_to_rgb(evt.color)
        swatch_w = 24
        draw.rectangle([lx, legend_y, lx + swatch_w, legend_y + 24], fill=color)
        text = f"{evt.name} · {evt.venue}"
        draw.text((lx + swatch_w + 10, legend_y + 2), text, fill=FG, font=legend_font)
        lx += swatch_w + 20 + int(draw.textlength(text, font=legend_font)) + 40

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
