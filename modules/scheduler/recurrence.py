"""
Recurring items: how often, and on which day (decision D2, roadmap step 1c).

The design, every decision and the exact rule: docs/scheduling/recurrence_design.md
("The rule as built"). In short, `frequency` on a habit, chore, task or routine:

- `daily`: on the plan every day. After a missed day, a small push the next day.
- weekday names (`tuesday`, `monday, thursday`): on those days only, as before.
- `weekly`, `monthly`, `quarterly`, `yearly`: once per period. On the plan from
  its turn until it is done (or its lighter version is), then gone until the
  next period. Its turn is the `day:` the pilot picked (weekly: a weekday;
  monthly: a day of the month), or else a day Chronos spreads it to, evenly over
  the period with the other items of that period that have no day, so no day
  gets a wall of chores (decision B, 2026-11-19). The push grows as the period
  runs out, on the same curve as commitments.

Nothing is stored: the same items give the same turns on every run (design
decision 3). Like direction.py, this module only reads YAML and returns plain
data; Kairos decides what to plan and Home what to say.
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import periods as Periods

# Score points at level 1.0, before the pilot's "Recurring Pressure" weight
# (scheduling_priorities.yml; 5 is neutral, 10 doubles, 0 switches it off).
# Calibration (design doc, "What the push does"): a chore on its last day (+24)
# ranks just above a task due today (+20) and just below a deadline today (+25);
# "on track" (0.2, +4.8) is a nudge like "due within three days" (+5).
RECURRING_MAX_BONUS = 24.0
# The push the day after a missed daily item, and after a missed period: the
# same "missed last time" step commitments get (direction.evaluate_commitment).
MISSED_PUSH = 0.2
# The row in scheduling_priorities.yml, as Kairos normalizes its name.
WEIGHT_NAME = "recurring_pressure"

PERIOD_WORDS = {"weekly": "week", "monthly": "month", "quarterly": "quarter", "yearly": "year"}
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_WEEKDAY_INDEX = {name: index for index, name in enumerate(WEEKDAYS)}
_WEEKDAY_INDEX.update({name[:3]: index for index, name in enumerate(WEEKDAYS)})
_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")
_LABEL = {"week": "Once a week", "month": "Once a month", "quarter": "Once a quarter", "year": "Once a year"}

# Statuses that take an item out of scheduling: the same set as
# kairos_v2.KairosV2Scheduler._is_inactive_status (tests/test_recurrence.py keeps
# them equal). A paused chore takes no turn, so it does not crowd the others.
INACTIVE_STATUSES = {"inactive", "archived", "disabled", "paused"}
# The library folders Kairos plans from (kairos_v2._iter_schedulable_library_items).
SCHEDULABLE_DIRS = {
    "habit": "habits",
    "task": "tasks",
    "routine": "routines",
    "subroutine": "subroutines",
    "microroutine": "microroutines",
    "timeblock": "timeblocks",
}


def _token(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_token(value: Any) -> str:
    # The same as kairos_v2._normalize_token, so frequencies read exactly as before.
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


# ------------------------------------------------------------------ frequency

def _frequency_tokens(frequency: Any) -> List[str]:
    """Split a frequency the way kairos_v2._frequency_applies_to_date always did."""
    if frequency is None:
        return []
    if isinstance(frequency, list):
        raw = frequency
    else:
        text = str(frequency).strip().lower()
        if not text:
            return []
        raw = text.replace("/", ",").split(",")
    return [token for token in (_normalize_token(value) for value in raw) if token]


def parse_frequency(frequency: Any) -> Dict[str, Any]:
    """
    What a `frequency` value means.

    rhythm: "daily", "weekdays" (with `weekdays`), "period" (with `period`:
    week, month, quarter or year), "unknown" (a value Chronos does not
    understand, never planned, as before) or "none" (no frequency).
    With several values `daily` wins, then the first period word, then weekday
    names; whatever else was written is listed in `ignored`.
    Weekday names must be written out in `frequency` (as before); `day:` also
    takes three-letter ones.
    """
    tokens = _frequency_tokens(frequency)
    info: Dict[str, Any] = {"rhythm": "none", "period": None, "weekdays": [], "ignored": []}
    if not tokens:
        return info
    if "daily" in tokens:
        info.update(rhythm="daily", ignored=[t for t in tokens if t != "daily"])
        return info
    period_words = [t for t in tokens if t in PERIOD_WORDS]
    if period_words:
        first = period_words[0]
        info.update(rhythm="period", period=PERIOD_WORDS[first], ignored=[t for t in tokens if t != first])
        return info
    weekdays = [t for t in tokens if t in WEEKDAYS]
    if weekdays:
        info.update(rhythm="weekdays", weekdays=weekdays, ignored=[t for t in tokens if t not in WEEKDAYS])
        return info
    info.update(rhythm="unknown", ignored=list(tokens))
    return info


# ----------------------------------------------------------------- its turn

def _day_number(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    text = str(value or "").strip()
    return int(text) if text.isdigit() else None


def preferred_day(value: Any, period: str, any_day: date) -> Tuple[Optional[date], Optional[str]]:
    """
    The day an item's `day:` picks in the period containing `any_day`.

    Weekly: a weekday (`saturday`, `Sat`). Monthly: a day of the month (`15`);
    a day the month does not have means its last day, so `31` is always the
    last day. Quarterly and yearly items cannot be given a day yet (design
    decision 7). Returns (day, None), (None, None) when no day was given, or
    (None, why) when the value cannot be used; the item is then spread.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, None
    start, end = Periods.period_bounds(any_day, period)
    if period == "week":
        index = _WEEKDAY_INDEX.get(value.strip().lower()) if isinstance(value, str) else None
        if index is not None:
            return start + timedelta(days=index), None
        return None, f"day: {value!r} is not a weekday (monday to sunday), so Chronos spreads it"
    if period == "month":
        number = _day_number(value)
        if number is not None and 1 <= number <= 31:
            return start + timedelta(days=min(number, end.day) - 1), None
        return None, f"day: {value!r} is not a day of the month (1 to 31), so Chronos spreads it"
    return None, f"day: is not read for {period}ly items yet, so Chronos spreads it"


def _nearest_least_busy(load: List[int], ideal: int) -> int:
    """The day nearest `ideal` with the least on it (a free day while there is one); earlier first."""
    least = min(load)
    for distance in range(len(load)):
        for offset in (ideal - distance, ideal + distance):
            if 0 <= offset < len(load) and load[offset] == least:
                return offset
    return ideal


def spread_turns(entries: Iterable[Dict[str, Any]], period: str, any_day: date) -> Dict[str, Dict[str, Any]]:
    """
    Each item's turn in the period containing `any_day`.

    `entries`: {"identity", "name", "day"} for every active item with this
    period. An item with a usable `day:` keeps it ("picked"). The others, sorted
    by name, are spaced evenly ("spread"): number i of n (from 0) gets day
    floor((2i + 1) x days in the period / 2n) of the period, counted from 0.
    A day that already holds a picked item gives way to the nearest free day,
    earlier first; with more items than days, the nearest of the least busy.
    The answer depends only on the items and the period, not on which day of
    the period is asked about, so every plan in the period sees the same turns.
    """
    start, end = Periods.period_bounds(any_day, period)
    length = (end - start).days + 1
    load = [0] * length
    out: Dict[str, Dict[str, Any]] = {}
    undated: List[str] = []
    ordered = sorted(entries, key=lambda e: (_token(e.get("name")), str(e.get("identity") or "")))
    for entry in ordered:
        identity = str(entry.get("identity") or "")
        if not identity or identity in out:
            continue
        picked, problem = preferred_day(entry.get("day"), period, any_day)
        if picked is not None:
            out[identity] = {"turn": picked, "source": "picked", "day_problem": None}
            load[(picked - start).days] += 1
        else:
            out[identity] = {"turn": None, "source": "spread", "day_problem": problem}
            undated.append(identity)
    count = len(undated)
    for index, identity in enumerate(undated):
        ideal = ((2 * index + 1) * length) // (2 * count)
        offset = _nearest_least_busy(load, ideal)
        load[offset] += 1
        out[identity]["turn"] = start + timedelta(days=offset)
    return out


# ------------------------------------------------------- is it on the plan today

def _curve(slack: int) -> Tuple[str, float]:
    """The commitment curve (direction.evaluate_commitment) for one thing still to do."""
    if slack <= 0:
        return "last_chance", 1.0
    if slack == 1:
        return "at_risk", 0.7
    if slack == 2:
        return "tightening", 0.45
    return "on_track", 0.2


def _ordinal(number: int) -> str:
    """1st, 2nd, 3rd, 4th, ... 11th, 12th, 13th, ... 21st, 22nd, 23rd, ... 31st."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _describe_day(day: date, period: str) -> str:
    if period == "week":
        return WEEKDAYS[day.weekday()].capitalize()
    if period == "month":
        return f"the {_ordinal(day.day)}"
    return f"{day.day} {_MONTHS[day.month - 1]}"


def describe_date(day: date) -> str:
    """'Thursday 16 April' (English on every machine, unlike strftime)."""
    return f"{WEEKDAYS[day.weekday()].capitalize()} {day.day} {_MONTHS[day.month - 1]}"


def _reason(period: str, target: date, turn: date, source: Optional[str], days_left: int, missed_previous: bool) -> str:
    word = "day" if source == "picked" else "turn"
    when = f"today is its {word}" if target == turn else f"missed its {word} ({_describe_day(turn, period)})"
    left = f"last chance this {period}" if days_left <= 1 else f"{days_left} days left this {period}"
    missed = f"; missed last {period} too" if missed_previous else ""
    return f"{_LABEL[period]}: {when}, {left}{missed}."


def evaluate(
    info: Dict[str, Any],
    target_date: date,
    done: Iterable[date],
    turn: Optional[date] = None,
    turn_source: Optional[str] = None,
    created: Optional[date] = None,
    skipped: Iterable[date] = (),
) -> Dict[str, Any]:
    """
    Where a recurring item stands on `target_date`.

    `skipped` (decision D9, 2026-11-19) holds the days its turn was skipped for
    the whole period ("Skip this week"): for a weekly to yearly item that turn is
    handled (state `skipped_turn`, not due, no push) and it does not count as
    "missed last time" in the next period. It is not a completion. Daily and
    weekday items ignore it (their Skip is always "not today").

    `info` comes from parse_frequency; `done` holds every day the item (or its
    lighter version) was done; `turn` / `turn_source` come from spread_turns;
    `created` is the day the item was made, when it says (design decision 9).
    Returns `due` (on the plan today), `state`, `level` (0-1 push), `reason`
    (a sentence for Home, or None), and the details behind them.
    """
    rhythm = info.get("rhythm")
    done_days = {day for day in (done or ()) if isinstance(day, date)}
    skipped_days = {day for day in (skipped or ()) if isinstance(day, date)}
    status: Dict[str, Any] = {
        "rhythm": rhythm, "period": info.get("period"), "due": False, "state": "", "level": 0.0,
        "missed_previous": False, "days_left": None, "turn": None, "turn_source": turn_source,
        "done_on": None, "reason": None,
    }
    if rhythm == "daily":
        yesterday = target_date - timedelta(days=1)
        # A push only for an item that has been done before: a brand-new daily
        # habit was not "missed" yesterday (as for commitments).
        missed = yesterday not in done_days and any(day < yesterday for day in done_days)
        status.update(due=True, state="missed_yesterday" if missed else "daily",
                      level=MISSED_PUSH if missed else 0.0,
                      reason="Daily: missed yesterday." if missed else None)
        return status
    if rhythm == "weekdays":
        on = WEEKDAYS[target_date.weekday()] in (info.get("weekdays") or [])
        status.update(due=on, state="fixed_day" if on else "not_today")
        return status
    if rhythm == "period":
        period = info.get("period") or "week"
        start, end = Periods.period_bounds(target_date, period)
        previous_start, previous_end = Periods.previous_period_bounds(target_date, period)
        days_left = (end - target_date).days + 1
        turn = turn if isinstance(turn, date) and start <= turn <= end else start
        status.update(days_left=days_left, turn=turn.isoformat())
        this_period = sorted(day for day in done_days if start <= day <= target_date)
        if this_period:
            status.update(state="done", done_on=this_period[-1].isoformat())
            return status
        skipped_this_period = sorted(day for day in skipped_days if start <= day <= target_date)
        if skipped_this_period:
            status.update(state="skipped_turn", skipped_on=skipped_this_period[-1].isoformat(),
                          reason=f"{_LABEL[period]}: skipped this {period}; back next {period}.")
            return status
        # Added after its turn had passed this period (design decision 9): it was
        # never missed, it did not exist yet. It starts with its next turn, so
        # setting up many chores mid-period does not pile up "missed" ones.
        if isinstance(created, date) and start <= created <= end and turn < created:
            status.update(state="starts_next_period")
            return status
        if target_date < turn:
            status.update(state="waiting")
            return status
        state, level = _curve(days_left - 1)
        # "Missed last time" only when the item was demonstrably around before
        # this period (it was done at some point), as for commitments.
        # A turn skipped on purpose last period (D9) was handled, not missed.
        missed_previous = (
            not any(previous_start <= day <= previous_end for day in done_days)
            and not any(previous_start <= day <= previous_end for day in skipped_days)
            and any(day < start for day in done_days)
        )
        if missed_previous:
            level = min(1.0, level + MISSED_PUSH)
        status.update(due=True, state=state, level=round(level, 3), missed_previous=missed_previous,
                      reason=_reason(period, target_date, turn, turn_source, days_left, missed_previous))
        return status
    status.update(state="unrecognised" if rhythm == "unknown" else "none")
    return status


def pressure_signal(status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    The signal direction.py hands Kairos and Home for an item, or None: only
    for an item on today's plan with a push (a turn that has come, or a daily
    item missed yesterday). Kairos scores it (direction.bonus_for) and counts
    it as importance on a tough day, never as urgency.
    """
    if not status.get("due") or float(status.get("level") or 0.0) <= 0:
        return None
    return {
        "name": status.get("name"),
        "period": status.get("period") or "day",
        "state": status.get("state"),
        "level": status.get("level"),
        "reason": status.get("reason"),
    }


# -------------------------------------------------------------------- loading

def read_library(user_dir: str) -> List[Dict[str, Any]]:
    """
    Every item in the folders Kairos plans from, with top-level keys lowercased
    (`Name:` is `name:`, as Kairos and item_manager read them).
    """
    items: List[Dict[str, Any]] = []
    for item_type, dirname in SCHEDULABLE_DIRS.items():
        folder = os.path.join(user_dir, dirname)
        if not os.path.isdir(folder):
            continue
        for filename in sorted(os.listdir(folder)):
            if not filename.endswith(".yml"):
                continue
            try:
                with open(os.path.join(folder, filename), "r", encoding="utf-8") as handle:
                    payload = Periods._load_yaml_text(handle.read())
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            item: Dict[str, Any] = {}
            for key, value in payload.items():
                lowered = str(key).lower()
                if lowered not in item or str(key) == lowered:
                    item[lowered] = value
            if not str(item.get("name") or "").strip():
                continue
            item.setdefault("type", item_type)
            items.append(item)
    return items


def _identity(item: Dict[str, Any]) -> str:
    return f"{_token(item.get('type'))}:{_token(item.get('name'))}"


def _is_active(item: Dict[str, Any]) -> bool:
    if _token(item.get("status")) in INACTIVE_STATUSES:
        return False
    # Kairos never plans bad habits (kairos_v2._is_bad_habit).
    return not (_token(item.get("type")) == "habit" and _token(item.get("polarity")) == "bad")


def log_window_start(target_date: date, items: Iterable[Dict[str, Any]]) -> date:
    """The earliest day whose completion log the recurring items need: yesterday, or the previous period's start."""
    earliest = target_date - timedelta(days=1)
    for item in items:
        info = parse_frequency(item.get("frequency"))
        if info["rhythm"] == "period":
            earliest = min(earliest, Periods.previous_period_bounds(target_date, info["period"])[0])
    return earliest


def evaluate_library(
    items: List[Dict[str, Any]],
    target_date: date,
    completed_by_date: Dict[date, set],
    skipped_by_date: Optional[Dict[date, set]] = None,
) -> Dict[str, Any]:
    """
    Every active recurring item's status on `target_date`.

    `skipped_by_date` (D9): Periods.turn_skips_by_date over the same window.

    Returns {"by_identity": {identity: status}, "unrecognised": [...]}. Each
    status is evaluate()'s, plus identity, name, type, frequency, day_problem
    and ignored. `completed_by_date` must reach back to log_window_start().
    """
    library_by_name: Dict[str, Dict[str, Any]] = {}
    for item in items:
        library_by_name.setdefault(_token(item.get("name")), item)

    active: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []
    entries_by_period: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        if not _is_active(item):
            continue
        info = parse_frequency(item.get("frequency"))
        if info["rhythm"] == "none":
            continue
        identity = _identity(item)
        if any(row[0] == identity for row in active):
            continue
        active.append((identity, item, info))
        if info["rhythm"] == "period":
            entries_by_period.setdefault(info["period"], []).append(
                {"identity": identity, "name": item.get("name"), "day": item.get("day")}
            )

    turns: Dict[str, Dict[str, Any]] = {}
    for period, entries in entries_by_period.items():
        turns.update(spread_turns(entries, period, target_date))

    by_identity: Dict[str, Dict[str, Any]] = {}
    unrecognised: List[Dict[str, Any]] = []
    for identity, item, info in active:
        name = str(item.get("name")).strip()
        names = [_token(name)] + Periods.mini_names_for(item, items)
        done = Periods.done_dates(item, names, library_by_name, completed_by_date)
        own = _token(name)
        skipped = [day for day, skipped_names in (skipped_by_date or {}).items() if own in skipped_names]
        turn_row = turns.get(identity) or {}
        created = Periods.parse_day(item.get("created"))
        status = evaluate(info, target_date, done, turn=turn_row.get("turn"), turn_source=turn_row.get("source"),
                          created=created, skipped=skipped)
        status.update({
            "identity": identity,
            "name": name,
            "type": _token(item.get("type")),
            "frequency": item.get("frequency"),
            "created": created.isoformat() if created else None,
            "day_problem": turn_row.get("day_problem"),
            "ignored": list(info.get("ignored") or []),
        })
        by_identity[identity] = status
        if info["rhythm"] == "unknown":
            unrecognised.append({"identity": identity, "name": name, "frequency": item.get("frequency")})
    return {"by_identity": by_identity, "unrecognised": unrecognised}


def load_recurring(user_dir: str, target_date: date) -> Dict[str, Any]:
    """read_library + the completion logs it needs + evaluate_library, in one call."""
    items = read_library(user_dir)
    window_start = log_window_start(target_date, items)
    completed_by_date = Periods.completed_names_by_date(user_dir, window_start, target_date)
    skipped_by_date = Periods.turn_skips_by_date(user_dir, window_start, target_date)
    return evaluate_library(items, target_date, completed_by_date, skipped_by_date)
