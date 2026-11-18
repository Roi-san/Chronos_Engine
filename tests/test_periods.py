"""
The shared helper for days and periods (roadmap step 1c, decision D2):
`modules/scheduler/periods.py`, docs/scheduling/recurrence_design.md.

Commitments (scheduler and tracker) and recurring items all ask it the same
questions: what day is it, where does this week / month / quarter / year start
and end, and on which days was something done. Some tests compare it with the
copies it replaces, so moving the code cannot change an answer unnoticed.
"""
import calendar
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta

import yaml

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from modules.scheduler import periods as Periods  # noqa: E402

# Wednesday 18 November 2026; its week runs Monday 16 to Sunday 22.
WEDNESDAY = date(2026, 11, 18)


def _write(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def _old_period_bounds(day, period):
    """direction.period_bounds as it was before step 1c (day, week, month; anything else a week)."""
    period = str(period or "").strip().lower() or "week"
    if period == "day":
        return day, day
    if period == "month":
        last = calendar.monthrange(day.year, day.month)[1]
        return day.replace(day=1), day.replace(day=last)
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def _old_period_key(d, period):
    """modules/commitment/main._period_key as it was before step 1c."""
    if period == "week":
        yr, wk, _ = d.isocalendar()
        return f"{yr}-W{wk:02d}"
    if period == "month":
        return d.strftime("%Y-%m")
    return d.strftime("%Y-%m-%d")


def _old_completed_names_by_date(user_dir, start, end):
    """direction._completed_names_by_date as it was before step 1c (frozen copy)."""
    out = {}
    folder = os.path.join(user_dir, "schedules", "completions")
    day = start
    while day <= end:
        path = os.path.join(folder, f"{day.isoformat()}.yml")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    payload = yaml.safe_load(handle) or {}
            except Exception:
                payload = {}
            entries = payload.get("entries") if isinstance(payload, dict) else None
            names = set()
            for key, raw in (entries.items() if isinstance(entries, dict) else []):
                entry = raw if isinstance(raw, dict) else {"status": raw}
                if str(entry.get("status") or "").strip().lower() not in ("completed", "done"):
                    continue
                name = entry.get("name") or (str(key).split("@", 1)[0] if "@" in str(key) else key)
                if str(name or "").strip().lower():
                    names.add(str(name).strip().lower())
            if names:
                out[day] = names
        day += timedelta(days=1)
    return out


def _old_done_dates(item, names, library_by_name, completed_by_date):
    """direction._done_dates as it was before step 1c (frozen copy)."""
    days = set()
    for name in names:
        source = library_by_name.get(name) or (item if item and str(item.get("name") or "").strip().lower() == name else None)
        for raw in (source.get("completion_dates") or []) if isinstance(source, dict) else []:
            try:
                days.add(date.fromisoformat(str(raw).strip()[:10]))
            except ValueError:
                pass
        for day, done in completed_by_date.items():
            if name in done:
                days.add(day)
    return days


class Today(unittest.TestCase):
    def test_today_is_the_calendar_date_of_now(self):
        self.assertEqual(Periods.today(datetime(2026, 11, 19, 1, 30)), date(2026, 11, 19))

    def test_without_an_argument_it_is_the_real_date(self):
        self.assertEqual(Periods.today(), date.today())


class NormalizePeriod(unittest.TestCase):
    def test_names_and_frequency_words(self):
        cases = {
            "day": "day", "daily": "day", "Week": "week", "weekly": "week", "MONTH": "month",
            "monthly": "month", "quarter": "quarter", "quarterly": "quarter", "year": "year",
            "yearly": "year", " Weekly ": "week",
        }
        for raw, expected in cases.items():
            self.assertEqual(Periods.normalize_period(raw), expected, raw)

    def test_unknown_values_are_empty(self):
        for raw in (None, "", "fortnight", "biweekly", 3):
            self.assertEqual(Periods.normalize_period(raw), "", raw)


class PeriodBounds(unittest.TestCase):
    def test_a_day(self):
        self.assertEqual(Periods.period_bounds(WEDNESDAY, "day"), (WEDNESDAY, WEDNESDAY))

    def test_a_week_runs_monday_to_sunday(self):
        week = (date(2026, 11, 16), date(2026, 11, 22))
        for day in (date(2026, 11, 16), WEDNESDAY, date(2026, 11, 22)):
            self.assertEqual(Periods.period_bounds(day, "week"), week, day)

    def test_months_of_every_length(self):
        self.assertEqual(Periods.period_bounds(WEDNESDAY, "month"), (date(2026, 11, 1), date(2026, 11, 30)))
        self.assertEqual(Periods.period_bounds(date(2026, 12, 31), "month"), (date(2026, 12, 1), date(2026, 12, 31)))
        self.assertEqual(Periods.period_bounds(date(2027, 2, 10), "month"), (date(2027, 2, 1), date(2027, 2, 28)))
        self.assertEqual(Periods.period_bounds(date(2028, 2, 10), "month"), (date(2028, 2, 1), date(2028, 2, 29)))

    def test_quarters_are_calendar_quarters(self):
        self.assertEqual(Periods.period_bounds(date(2026, 1, 1), "quarter"), (date(2026, 1, 1), date(2026, 3, 31)))
        self.assertEqual(Periods.period_bounds(date(2026, 5, 15), "quarter"), (date(2026, 4, 1), date(2026, 6, 30)))
        self.assertEqual(Periods.period_bounds(date(2026, 9, 30), "quarter"), (date(2026, 7, 1), date(2026, 9, 30)))
        self.assertEqual(Periods.period_bounds(WEDNESDAY, "quarter"), (date(2026, 10, 1), date(2026, 12, 31)))

    def test_a_year(self):
        self.assertEqual(Periods.period_bounds(WEDNESDAY, "year"), (date(2026, 1, 1), date(2026, 12, 31)))

    def test_frequency_words_mean_their_period(self):
        self.assertEqual(Periods.period_bounds(WEDNESDAY, "weekly"), Periods.period_bounds(WEDNESDAY, "week"))
        self.assertEqual(Periods.period_bounds(WEDNESDAY, "quarterly"), Periods.period_bounds(WEDNESDAY, "quarter"))

    def test_an_unknown_period_is_a_week_as_before(self):
        self.assertEqual(Periods.period_bounds(WEDNESDAY, "fortnight"), (date(2026, 11, 16), date(2026, 11, 22)))
        self.assertEqual(Periods.period_bounds(WEDNESDAY, ""), (date(2026, 11, 16), date(2026, 11, 22)))

    def test_same_answers_as_the_old_direction_code_for_day_week_month(self):
        day = date(2025, 12, 20)
        while day <= date(2027, 1, 10):
            for period in ("day", "week", "month", "", "fortnight"):
                self.assertEqual(Periods.period_bounds(day, period), _old_period_bounds(day, period), (day, period))
            day += timedelta(days=1)


class PreviousPeriodAndLength(unittest.TestCase):
    def test_previous_periods_cross_year_boundaries(self):
        jan = date(2027, 1, 5)
        self.assertEqual(Periods.previous_period_bounds(jan, "month"), (date(2026, 12, 1), date(2026, 12, 31)))
        self.assertEqual(Periods.previous_period_bounds(jan, "quarter"), (date(2026, 10, 1), date(2026, 12, 31)))
        self.assertEqual(Periods.previous_period_bounds(jan, "year"), (date(2026, 1, 1), date(2026, 12, 31)))
        self.assertEqual(Periods.previous_period_bounds(WEDNESDAY, "week"), (date(2026, 11, 9), date(2026, 11, 15)))

    def test_lengths(self):
        self.assertEqual(Periods.period_length(WEDNESDAY, "week"), 7)
        self.assertEqual(Periods.period_length(WEDNESDAY, "month"), 30)
        self.assertEqual(Periods.period_length(date(2028, 2, 1), "month"), 29)
        self.assertEqual(Periods.period_length(WEDNESDAY, "quarter"), 92)
        self.assertEqual(Periods.period_length(WEDNESDAY, "year"), 365)
        self.assertEqual(Periods.period_length(date(2028, 6, 1), "year"), 366)


class PeriodKeys(unittest.TestCase):
    def test_keys(self):
        self.assertEqual(Periods.period_key(WEDNESDAY, "day"), "2026-11-18")
        self.assertEqual(Periods.period_key(WEDNESDAY, "week"), "2026-W47")
        self.assertEqual(Periods.period_key(WEDNESDAY, "month"), "2026-11")
        self.assertEqual(Periods.period_key(WEDNESDAY, "quarter"), "2026-Q4")
        self.assertEqual(Periods.period_key(WEDNESDAY, "year"), "2026")

    def test_week_month_and_day_keys_match_what_commitments_already_stored(self):
        # `last_met` / `last_violation` in commitment files hold these keys.
        day = date(2025, 12, 20)
        while day <= date(2027, 1, 10):
            for period in ("day", "week", "month"):
                self.assertEqual(Periods.period_key(day, period), _old_period_key(day, period), (day, period))
            day += timedelta(days=1)


class CompletionLogs(unittest.TestCase):
    def setUp(self):
        self.user_dir = tempfile.mkdtemp()
        folder = os.path.join(self.user_dir, "schedules", "completions")
        _write(os.path.join(folder, "2026-11-16.yml"), {"entries": {
            "Laundry@09:00": {"name": "Laundry", "status": "completed"},
            "Dishes@10:00": {"name": "Dishes", "status": "skipped"},
        }})
        _write(os.path.join(folder, "2026-11-17.yml"), {"entries": {
            "Vacuum@11:00": {"status": "done"},              # name only in the key
            "Mop@12:00": "completed",                          # older plain-string form
            "Plants@13:00": {"name": "Plants", "status": "missed"},
        }})
        _write(os.path.join(folder, "2026-10-01.yml"), {"entries": {"Old@09:00": {"name": "Old", "status": "completed"}}})
        with open(os.path.join(folder, "2026-11-18.yml"), "w", encoding="utf-8") as handle:
            handle.write("entries: [this is: not: valid\n")
        with open(os.path.join(folder, "notes.yml"), "w", encoding="utf-8") as handle:
            handle.write("entries: {}\n")

    def tearDown(self):
        shutil.rmtree(self.user_dir, ignore_errors=True)

    def test_completed_and_done_count_by_day(self):
        out = Periods.completed_names_by_date(self.user_dir, date(2026, 11, 1), date(2026, 11, 30))
        self.assertEqual(out, {date(2026, 11, 16): {"laundry"}, date(2026, 11, 17): {"vacuum", "mop"}})

    def test_the_range_is_respected(self):
        out = Periods.completed_names_by_date(self.user_dir, date(2026, 9, 1), date(2026, 11, 16))
        self.assertEqual(set(out), {date(2026, 10, 1), date(2026, 11, 16)})

    def test_no_folder_gives_nothing(self):
        self.assertEqual(Periods.completed_names_by_date(tempfile.gettempdir() + "/no-such-chronos-user", date(2026, 1, 1), date(2026, 12, 31)), {})

    def test_same_answers_as_the_old_direction_code(self):
        old = _old_completed_names_by_date(self.user_dir, date(2026, 9, 1), date(2026, 11, 30))
        new = Periods.completed_names_by_date(self.user_dir, date(2026, 9, 1), date(2026, 11, 30))
        self.assertEqual(new, old)

    def test_the_fast_parser_reads_logs_the_same_way(self):
        path = os.path.join(self.user_dir, "schedules", "completions", "2026-11-17.yml")
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        self.assertEqual(Periods._load_yaml_text(text), yaml.safe_load(text))


class DoneDates(unittest.TestCase):
    def test_item_history_logs_and_lighter_versions_all_count(self):
        item = {"name": "Clean bathroom", "completion_dates": ["2026-11-02", "not a date"]}
        library = {
            "clean bathroom": item,
            "quick wipe": {"name": "Quick wipe", "mini_of": "Clean bathroom", "completion_dates": ["2026-11-09"]},
        }
        logs = {date(2026, 11, 16): {"clean bathroom"}, date(2026, 11, 17): {"something else"}}
        days = Periods.done_dates(item, ["clean bathroom", "quick wipe"], library, logs)
        self.assertEqual(days, {date(2026, 11, 2), date(2026, 11, 9), date(2026, 11, 16)})

    def test_same_answers_as_the_old_direction_code(self):
        item = {"name": "Gym", "completion_dates": ["2026-11-02"]}
        library = {"gym": item, "mobility": {"name": "Mobility", "completion_dates": ["2026-11-03"]}}
        logs = {date(2026, 11, 4): {"gym"}, date(2026, 11, 5): {"mobility"}}
        self.assertEqual(
            Periods.done_dates(item, ["gym", "mobility"], library, logs),
            _old_done_dates(item, ["gym", "mobility"], library, logs),
        )


class DirectionUsesTheHelper(unittest.TestCase):
    """direction.py keeps its old names, now pointing at the shared helper."""

    def test_old_names_still_work(self):
        from modules.scheduler import direction as Direction
        self.assertEqual(Direction.period_bounds(WEDNESDAY, "month"), Periods.period_bounds(WEDNESDAY, "month"))
        self.assertEqual(Direction.previous_period_bounds(WEDNESDAY, "week"), Periods.previous_period_bounds(WEDNESDAY, "week"))
        self.assertIs(Direction.period_bounds, Periods.period_bounds)


if __name__ == "__main__":
    unittest.main()
