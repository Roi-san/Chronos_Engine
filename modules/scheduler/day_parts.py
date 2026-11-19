"""
Parts of the day: what `when:` on an item means (decision D8, 2026-11-19).

Design: `docs/scheduling/planning_and_tracking_model.md`, proposal C. An item's
`when` is either a clock time ("21:00", the same as `start_time`) or a part of
the day. Both are wishes (decision D7): Kairos keeps them when there is room,
else plans the item like any other and says why
(`kairos_v2._place_wished_times`).

The parts follow your own day, not a fixed clock at both ends:
- morning:    from waking up (the end of the day's sleep block) to 12:00
- afternoon:  12:00 to 17:00
- evening:    17:00 to bedtime
- before bed: the last two hours before bedtime; an item placed here ends as
              close to bedtime as possible (the pilot, 2026-11-19: "before bed"
              is a part of its own, the most intuitive answer)

"Bedtime" is where today's plan ends (`schedule.day_budget.sleep_boundary_minutes`):
the start of the sleep block, or 23:59 for a bedtime after midnight until the
night-owl day (issue 9) exists. Without a sleep block, waking up is 07:00.

The forms (Home's capture box, the Routine Builder) offer exactly the values in
`PART_LABELS` and write them as `when: morning` and so on.
"""
from __future__ import annotations

import re
from typing import Any, Optional, Tuple

PART_LABELS = {
    "morning": "the morning",
    "afternoon": "the afternoon",
    "evening": "the evening",
    "before_bed": "just before bed",
}
_ALIASES = {
    "morning": "morning",
    "afternoon": "afternoon",
    "evening": "evening",
    "before bed": "before_bed",
    "bedtime": "before_bed",
}
NOON = 12 * 60
FIVE_PM = 17 * 60
BEFORE_BED_MINUTES = 120
DEFAULT_WAKE = 7 * 60
_TIME = re.compile(r"^(\d{1,2}):(\d{2})$")


def parse_when(value: Any) -> Optional[Tuple[str, Any]]:
    """("time", minutes) | ("part", name) | ("unknown", text) | None for nothing set."""
    text = str(value or "").strip()
    if not text:
        return None
    match = _TIME.match(text)
    if match:
        hours, minutes = int(match.group(1)), int(match.group(2))
        if hours < 24 and minutes < 60:
            return ("time", hours * 60 + minutes)
    # "Before bed", "before_bed", "before-bed" and "  before   bed" are one value.
    part = _ALIASES.get(" ".join(text.lower().replace("_", " ").replace("-", " ").split()))
    if part:
        return ("part", part)
    return ("unknown", text)


def window(part: str, *, wake: int, bed: int) -> Tuple[int, int]:
    """(start, end) minutes of a part of the day, given waking up and bedtime."""
    if part == "morning":
        return (wake, NOON)
    if part == "afternoon":
        return (NOON, FIVE_PM)
    if part == "evening":
        return (FIVE_PM, bed)
    if part == "before_bed":
        return (max(0, bed - BEFORE_BED_MINUTES), bed)
    raise ValueError(f"unknown part of the day: {part}")


def latest_first(part: str) -> bool:
    """Whether an item in this part goes as late as possible (before bed) or as early."""
    return part == "before_bed"


def label(part: str) -> str:
    return PART_LABELS.get(part, part)
