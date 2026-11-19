"""
Days and periods: the one place Chronos answers three questions.

1. What day is it? (`today`)
2. Where does this day, week, month, quarter or year start and end?
   (`period_bounds`, `previous_period_bounds`, `period_length`, `period_key`)
3. On which days was something done? (`completed_names_by_date`, `done_dates`,
   with `mini_names_for`: a lighter version counts as the item.)

Added in roadmap step 1c (decision D2, docs/scheduling/recurrence_design.md).
Commitments (the scheduler side in direction.py and the tracker in
modules/commitment/main.py) and recurring items (recurrence.py) all ask these
questions. Before, commitments had two copies of the period code that could
disagree. With one copy they cannot, and when "a day that lasts until bedtime"
(issue 9 in docs/ISSUES_AND_NEXT_STEPS.md) is built, `today` changes here
instead of in every caller.

It only reads YAML and returns plain data. Nothing here knows about Kairos.
"""
from __future__ import annotations

import calendar
import os
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import yaml

PERIODS = ("day", "week", "month", "quarter", "year")

# Period names, and the frequency words people write for them.
_PERIOD_WORDS = {
    "day": "day", "daily": "day",
    "week": "week", "weekly": "week",
    "month": "month", "monthly": "month",
    "quarter": "quarter", "quarterly": "quarter",
    "year": "year", "yearly": "year",
}

# PyYAML's C parser when it is installed: the same results, about seven times
# faster on the daily completion logs (measured on the pilot's machine: 62 days
# of logs in 28 ms instead of 199 ms). The plain parser otherwise.
_YAML_LOADER = getattr(yaml, "CSafeLoader", None) or yaml.SafeLoader

_LOG_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})\.yml$", re.IGNORECASE)


def _token(value: Any) -> str:
    return str(value or "").strip().lower()


def _load_yaml_text(text: str) -> Any:
    return yaml.load(text, Loader=_YAML_LOADER)


# --------------------------------------------------------------------- the day

def today(now: Optional[datetime] = None) -> date:
    """
    What day it is: for now, the calendar date of `now` (default: the clock).

    Chronos counts a day from midnight to midnight everywhere. When "a day that
    lasts until bedtime" is built (issue 9), this is the function to change.
    """
    return (now or datetime.now()).date()


# ----------------------------------------------------------------- the periods

def normalize_period(value: Any) -> str:
    """'week' for week/weekly/Week, and so on; '' for anything else."""
    return _PERIOD_WORDS.get(_token(value), "")


def period_bounds(day: date, period: Any) -> Tuple[date, date]:
    """
    First and last day of the period containing `day`.

    Weeks run Monday to Sunday (the ISO week). Months, quarters (January-March,
    April-June, July-September, October-December) and years are calendar ones.
    Anything that is not a period counts as a week, as it always did for
    commitments (direction.period_bounds before step 1c).
    """
    kind = normalize_period(period) or "week"
    if kind == "day":
        return day, day
    if kind == "month":
        return day.replace(day=1), day.replace(day=calendar.monthrange(day.year, day.month)[1])
    if kind == "quarter":
        first_month = 3 * ((day.month - 1) // 3) + 1
        last_month = first_month + 2
        return (
            date(day.year, first_month, 1),
            date(day.year, last_month, calendar.monthrange(day.year, last_month)[1]),
        )
    if kind == "year":
        return date(day.year, 1, 1), date(day.year, 12, 31)
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def previous_period_bounds(day: date, period: Any) -> Tuple[date, date]:
    start, _ = period_bounds(day, period)
    return period_bounds(start - timedelta(days=1), period)


def period_length(day: date, period: Any) -> int:
    start, end = period_bounds(day, period)
    return (end - start).days + 1


def period_key(day: date, period: Any) -> str:
    """
    A short name for the period, the same for every day in it: '2026-11-18',
    '2026-W47' (the ISO week), '2026-11', '2026-Q4', '2026'.

    The day, week and month forms are the ones commitment files already store
    in `last_met` / `last_violation`, so they must not change.
    """
    kind = normalize_period(period) or "week"
    if kind == "day":
        return day.isoformat()
    if kind == "month":
        return day.strftime("%Y-%m")
    if kind == "quarter":
        return f"{day.year}-Q{(day.month - 1) // 3 + 1}"
    if kind == "year":
        return str(day.year)
    iso_year, iso_week, _ = day.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


# ------------------------------------------------------- what was done, when

def parse_day(value: Any) -> Optional[date]:
    """A date from a date, a datetime, or text starting with YYYY-MM-DD; else None."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def completed_names_by_date(user_dir: str, start: date, end: date) -> Dict[date, Set[str]]:
    """
    Names logged as completed (or done) on each day from `start` to `end`, from
    the daily completion logs in `<user_dir>/schedules/completions/`. Names are
    lowercase. Skipped, missed and other entries are not completions.

    Home's Done button (`mark`), `complete`, `did` and Start day all write these
    logs, and Start day writes nothing else (issue 24), so every "was it done"
    question must read them as well as an item's own `completion_dates`.

    Moved here from direction._completed_names_by_date (same answers); it now
    lists the folder once instead of checking every date, and uses the fast
    YAML parser.
    """
    return _names_by_date(user_dir, start, end, lambda entry: _token(entry.get("status")) in ("completed", "done"))


def turn_skips_by_date(user_dir: str, start: date, end: date) -> Dict[date, Set[str]]:
    """
    Names whose turn was skipped for the whole period on each day ("Skip this
    week", decision D9, 2026-11-19): log entries with `status: skipped` and
    `skip: period`. A plain skip ("not today") is not one. A skipped turn is not
    a completion: only recurrence reads it (handled for the period).
    """
    return _names_by_date(
        user_dir, start, end,
        lambda entry: _token(entry.get("status")) == "skipped" and _token(entry.get("skip")) == "period",
    )


def _names_by_date(user_dir: str, start: date, end: date, keep) -> Dict[date, Set[str]]:
    """The lowercase names of the log entries `keep` accepts, per day from `start` to `end`."""
    out: Dict[date, Set[str]] = {}
    folder = os.path.join(user_dir, "schedules", "completions")
    try:
        filenames = os.listdir(folder)
    except OSError:
        return out
    for filename in filenames:
        match = _LOG_NAME.match(filename)
        if not match:
            continue
        day = parse_day(match.group(1))
        if day is None or day < start or day > end:
            continue
        try:
            with open(os.path.join(folder, filename), "r", encoding="utf-8") as handle:
                payload = _load_yaml_text(handle.read()) or {}
        except Exception:
            continue
        entries = payload.get("entries") if isinstance(payload, dict) else None
        names: Set[str] = set()
        for key, raw in (entries.items() if isinstance(entries, dict) else []):
            entry = raw if isinstance(raw, dict) else {"status": raw}
            if not keep(entry):
                continue
            name = entry.get("name") or (str(key).split("@", 1)[0] if "@" in str(key) else key)
            if _token(name):
                names.add(_token(name))
        if names:
            out[day] = names
    return out


def mini_names_for(item: Optional[Dict[str, Any]], library: Iterable[Dict[str, Any]]) -> List[str]:
    """
    Names of the lighter versions of an item: the one it points to through
    `mini_variant`, and any item pointing back at it through `mini_of`.
    Doing a lighter version counts as doing the item, for commitments and for
    recurring items alike. (Moved here from direction.mini_names_for, unchanged.)
    """
    if not isinstance(item, dict):
        return []

    def slug(value: Any) -> str:
        text = _token(value)
        text = text.split(":", 1)[1] if ":" in text else text
        return text.replace(" ", "_").replace("-", "_")

    name = _token(item.get("name"))
    wanted_name = slug(item.get("mini_variant"))
    names: List[str] = []
    for other in library:
        other_name = _token(other.get("name"))
        if not other_name or other_name == name:
            continue
        points_back = slug(other.get("mini_of"))
        if (wanted_name and slug(other_name) == wanted_name) or (points_back and points_back == slug(name)):
            if other_name not in names:
                names.append(other_name)
    return names


def done_dates(
    item: Optional[Dict[str, Any]],
    names: Iterable[str],
    library_by_name: Dict[str, Dict[str, Any]],
    completed_by_date: Dict[date, set],
) -> Set[date]:
    """
    Every day one of `names` (lowercase: the item and its lighter versions) was
    completed: each one's own `completion_dates`, plus the daily logs.
    (Moved here from direction._done_dates, unchanged apart from reading a
    datetime as its date.)
    """
    days: Set[date] = set()
    for name in names:
        source = library_by_name.get(name) or (item if item and _token(item.get("name")) == name else None)
        for raw in (source.get("completion_dates") or []) if isinstance(source, dict) else []:
            parsed = parse_day(raw)
            if parsed:
                days.add(parsed)
        for day, done in completed_by_date.items():
            if name in done:
                days.add(day)
    return days
