"""
"Skip this week" for items that repeat weekly or less often (decision D9,
2026-11-19; proposal D in `docs/scheduling/planning_and_tracking_model.md`).

Home's Skip means "not today": the item comes back tomorrow with a little more
push (D2). For a weekly, monthly, quarterly or yearly item Home now also offers
"Skip this week" (month, quarter, year): `mark "<name>":skipped` with
`skip: period`, written to the day's completion log as `status: skipped` plus
`skip: period`, so every older reader still sees an ordinary skip. Recurrence
reads the field: the turn is handled for this period (not due, no push), it is
not "missed last time" next period, and it is not done (streaks, commitments
and goals do not count it). The pilot's explicit choice wins for the period:
a goal or commitment does not bring the item back before its next turn.

Fixture clock: Thursday 16 April 2026 (week Mon 13 to Sun 19).
"""
import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime

import yaml

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from chronos_fixture import temporary_kairos_user_fixture  # noqa: E402
from modules.scheduler import periods as Periods  # noqa: E402
from modules.scheduler import recurrence as Recurrence  # noqa: E402
from modules.scheduler.kairos_v2 import KairosV2Scheduler  # noqa: E402
from test_kairos_v2_direction import _seed, _write  # noqa: E402
from test_wished_time import DAY  # noqa: E402
from utilities.dashboard import home_api  # noqa: E402

THU, FRI = date(2026, 4, 16), date(2026, 4, 17)
LAUNDRY = {"name": "Laundry", "type": "habit", "duration": 60, "frequency": "weekly", "day": "thursday",
           "created": "2026-01-01"}


def log(user, day, entries):
    _write(os.path.join(user, "schedules", "completions", f"{day.isoformat()}.yml"), {"entries": entries})


def skip_entry(name, scope=True):
    entry = {"name": name, "status": "skipped", "scheduled_start": "17:00", "scheduled_end": "18:00",
             "logged_at": "2026-04-16T17:05:00"}
    if scope:
        entry["skip"] = "period"
    return {f"{name}@17:00": entry}


def plan(day, files, logs=None):
    now = datetime(day.year, day.month, day.day, 8, 0)
    with temporary_kairos_user_fixture() as fixture:
        user = fixture["user_dir"]
        for name in os.listdir(os.path.join(user, "days")):
            os.remove(os.path.join(user, "days", name))
        _write(os.path.join(user, "days", "my_day.yml"), DAY)
        _seed(user, files)
        for log_day, entries in (logs or {}).items():
            log(user, log_day, entries)
        with redirect_stdout(io.StringIO()):
            result = KairosV2Scheduler({"now": now}).generate_schedule(day)
    return result.get("schedule", {})


def planned(schedule, name):
    names = []

    def walk(blocks):
        for block in blocks or []:
            names.append(block.get("name"))
            walk(block.get("children"))

    walk(schedule.get("conceptual_schedule", {}).get("conceptual_blocks"))
    return name in names


def recurring_state(schedule, identity="habit:laundry"):
    rows = (schedule.get("recurring") or {}).get("items") or []
    return next((row.get("state") for row in rows if row.get("identity") == identity), None)


class Evaluate(unittest.TestCase):
    INFO = Recurrence.parse_frequency("weekly")

    def test_a_skipped_turn_is_handled_for_the_period(self):
        status = Recurrence.evaluate(self.INFO, THU, done=[], turn=THU, skipped=[THU])
        self.assertFalse(status["due"])
        self.assertEqual(status["state"], "skipped_turn")
        self.assertEqual(status["level"], 0.0)

    def test_a_skipped_turn_is_not_missed_last_time(self):
        next_thu = date(2026, 4, 23)
        done = [date(2026, 4, 2)]
        without = Recurrence.evaluate(self.INFO, next_thu, done=done, turn=next_thu)
        with_skip = Recurrence.evaluate(self.INFO, next_thu, done=done, turn=next_thu, skipped=[THU])
        self.assertTrue(without["missed_previous"])
        self.assertFalse(with_skip["missed_previous"])
        self.assertTrue(with_skip["due"])                       # its new turn has come

    def test_daily_items_ignore_it(self):
        status = Recurrence.evaluate(Recurrence.parse_frequency("daily"), THU, done=[], skipped=[THU])
        self.assertTrue(status["due"])

    def test_the_log_reader(self):
        with temporary_kairos_user_fixture() as fixture:
            log(fixture["user_dir"], THU, {**skip_entry("Laundry"), **skip_entry("Vacuum", scope=False)})
            skipped = Periods.turn_skips_by_date(fixture["user_dir"], THU, FRI)
        self.assertEqual(skipped, {THU: {"laundry"}})


class ThePlan(unittest.TestCase):
    def test_skipped_this_week_is_not_back_on_friday(self):
        s = plan(FRI, {"habits/laundry.yml": LAUNDRY}, {THU: skip_entry("Laundry")})
        self.assertFalse(planned(s, "Laundry"))
        self.assertEqual(recurring_state(s), "skipped_turn")
        self.assertEqual(s["recurring"]["skipped_this_period"], [f"Laundry: skipped on {Recurrence.describe_date(THU)}"])

    def test_a_plain_skip_still_brings_it_back_on_friday(self):
        s = plan(FRI, {"habits/laundry.yml": LAUNDRY}, {THU: skip_entry("Laundry", scope=False)})
        self.assertTrue(planned(s, "Laundry"))

    def test_a_goal_does_not_bring_a_skipped_turn_back(self):
        goal = {"name": "Tidy home", "type": "goal", "status": "active", "priority": "high"}
        s = plan(FRI, {"habits/laundry.yml": {**LAUNDRY, "goal": "Tidy home"}, "goals/tidy.yml": goal},
                 {THU: skip_entry("Laundry")})
        self.assertFalse(planned(s, "Laundry"))

    def test_back_on_its_turn_next_week(self):
        s = plan(date(2026, 4, 23), {"habits/laundry.yml": LAUNDRY}, {THU: skip_entry("Laundry")})
        self.assertTrue(planned(s, "Laundry"))


class TheMarkCommand(unittest.TestCase):
    def _mark(self, args, properties):
        from commands import mark as Mark
        from modules.scheduler import schedule_path_for_date
        with temporary_kairos_user_fixture() as fixture:
            user = fixture["user_dir"]
            _seed(user, {"habits/laundry.yml": LAUNDRY})
            _write(schedule_path_for_date("2026-04-16"), {"items": [
                {"name": "Laundry", "type": "habit", "start_time": "17:00", "end_time": "18:00"}]})
            with redirect_stdout(io.StringIO()):
                Mark.run(args, {**properties, "date": "2026-04-16"})
            with open(os.path.join(user, "schedules", "completions", "2026-04-16.yml"), encoding="utf-8") as handle:
                entries = (yaml.safe_load(handle) or {}).get("entries") or {}
        return list(entries.values())

    def test_as_home_sends_it(self):
        [entry] = self._mark(["Laundry:skipped"], {"skip": "period"})
        self.assertEqual((entry["status"], entry.get("skip")), ("skipped", "period"))

    def test_from_the_console(self):
        # `mark "Laundry":skipped skip:period`: the console turns both tokens into properties.
        [entry] = self._mark([], {"Laundry": "skipped", "skip": "period"})
        self.assertEqual((entry["status"], entry.get("skip")), ("skipped", "period"))

    def test_a_plain_skip_has_no_field(self):
        [entry] = self._mark(["Laundry:skipped"], {})
        self.assertNotIn("skip", entry)


class Home(unittest.TestCase):
    def test_which_blocks_offer_skip_this_turn(self):
        meta = {"recurring": {"items": [
            {"name": "Laundry", "rhythm": "period", "period": "week", "state": "on_track"},
            {"name": "Meditate", "rhythm": "daily", "period": None, "state": "missed_yesterday"},
        ]}}
        self.assertEqual(home_api.turn_periods(meta), {"laundry": "week"})

    def test_a_skipped_turn_stays_visible(self):
        meta = {"recurring": {"items": [
            {"name": "Laundry", "rhythm": "period", "period": "week", "state": "skipped_turn"},
        ]}}
        self.assertEqual(home_api.plan_notes(meta), ["Skipped this week: Laundry. It is back next week."])


if __name__ == "__main__":
    unittest.main()
