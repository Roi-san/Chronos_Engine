"""Habits: a safety net (roadmap step 1b, 2026-11-18).

`modules/habit/main.py` did not parse upstream for a long time (since polarity
was added), and nothing noticed: `item_manager.dispatch_command` silently falls
back to the generic handlers when a module fails to load. Recurring items
(decision D2, `docs/scheduling/recurrence_design.md`) will depend on habit
completion history, so these tests pin what habits do today, through the same
paths the console uses:

- the habit module is the one that runs, not the generic fallback;
- `new`, `complete`, `track`, `delete`;
- `completion_dates`, `last_completed`, streaks; incidents for bad habits;
- `complete habit` through `commands/complete.py` also writes today's
  completion log, which Kairos reads to drop done items from a re-plan.

They describe current behaviour; none needed a code change.
"""

import contextlib
import importlib.util
import io
import os
import sys
import unittest
from datetime import datetime, timedelta

import yaml

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from chronos_fixture import temporary_kairos_user_fixture  # noqa: E402
from commands import complete as Complete  # noqa: E402
from modules.item_manager import dispatch_command, read_item_data  # noqa: E402
from modules.scheduler.kairos_v2 import KairosV2Scheduler  # noqa: E402

TODAY = datetime.now().strftime("%Y-%m-%d")


def _days_ago(n):
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


def _write(user_dir, rel_path, payload):
    path = os.path.join(user_dir, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def _quiet(fn, *args, **kwargs):
    """Run fn, return what it printed."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        fn(*args, **kwargs)
    return buffer.getvalue()


STRETCH = {"name": "Stretch", "type": "habit", "frequency": "daily", "duration": 10, "polarity": "good"}


class TheHabitModuleRuns(unittest.TestCase):
    def test_the_module_file_loads_the_way_dispatch_loads_it(self):
        path = os.path.join(ROOT_DIR, "modules", "habit", "main.py")
        spec = importlib.util.spec_from_file_location("chronos_module.habit_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # raises if the file does not parse
        self.assertTrue(callable(getattr(module, "handle_command", None)))

    def test_dispatch_reaches_the_habit_module(self):
        # The generic handlers have no `complete`; only the habit module records it.
        with temporary_kairos_user_fixture() as fixture:
            _write(fixture["user_dir"], "habits/stretch.yml", STRETCH)
            _quiet(dispatch_command, "complete", "habit", "Stretch", None, {})
            self.assertIn(TODAY, read_item_data("habit", "Stretch").get("completion_dates") or [])


class NewHabit(unittest.TestCase):
    def test_new_writes_the_given_properties(self):
        with temporary_kairos_user_fixture():
            _quiet(dispatch_command, "new", "habit", "Floss", None, {"frequency": "daily", "duration": 5})
            habit = read_item_data("habit", "Floss")
            self.assertEqual(habit.get("name"), "Floss")
            self.assertEqual(str(habit.get("type")).lower(), "habit")
            self.assertEqual(str(habit.get("frequency")).lower(), "daily")
            self.assertEqual(int(habit.get("duration")), 5)


class CompleteHabit(unittest.TestCase):
    def _complete(self, habit):
        with temporary_kairos_user_fixture() as fixture:
            _write(fixture["user_dir"], f"habits/{habit['name'].lower()}.yml", habit)
            out = _quiet(dispatch_command, "complete", "habit", habit["name"], None, {})
            return read_item_data("habit", habit["name"]), out

    def test_a_first_completion_records_today_and_starts_a_streak(self):
        habit, _ = self._complete(dict(STRETCH))
        self.assertEqual(habit["completion_dates"], [TODAY])
        self.assertEqual(str(habit["last_completed"]), TODAY)
        self.assertEqual((habit["current_streak"], habit["longest_streak"]), (1, 1))

    def test_a_second_completion_today_changes_nothing(self):
        habit, out = self._complete({**STRETCH, "completion_dates": [TODAY], "last_completed": TODAY,
                                     "current_streak": 2, "longest_streak": 2})
        self.assertEqual(habit["completion_dates"], [TODAY])
        self.assertEqual(habit["current_streak"], 2)
        self.assertIn("already been completed today", out)

    def test_done_yesterday_grows_the_streak(self):
        habit, _ = self._complete({**STRETCH, "last_completed": _days_ago(1), "completion_dates": [_days_ago(1)],
                                   "current_streak": 3, "longest_streak": 3})
        self.assertEqual((habit["current_streak"], habit["longest_streak"]), (4, 4))
        self.assertEqual(habit["completion_dates"], [_days_ago(1), TODAY])

    def test_a_gap_restarts_the_streak_and_keeps_the_longest(self):
        habit, _ = self._complete({**STRETCH, "last_completed": _days_ago(3), "current_streak": 5, "longest_streak": 7})
        self.assertEqual((habit["current_streak"], habit["longest_streak"]), (1, 7))

    def test_a_bad_habit_records_an_incident_not_a_streak(self):
        habit, out = self._complete({"name": "Doomscroll", "type": "habit", "polarity": "bad",
                                     "last_incident": _days_ago(4), "clean_longest_streak": 2})
        self.assertEqual(habit["incident_dates"], [TODAY])
        self.assertEqual(str(habit["last_incident"]), TODAY)
        self.assertEqual(habit["clean_current_streak"], 0)
        self.assertEqual(habit["clean_longest_streak"], 4)
        self.assertNotIn("current_streak", habit)
        self.assertIn("Recorded incident", out)

    def test_an_unknown_habit_is_reported_and_not_created(self):
        with temporary_kairos_user_fixture():
            out = _quiet(dispatch_command, "complete", "habit", "Nope", None, {})
            self.assertIn("not found", out)
            self.assertFalse(read_item_data("habit", "Nope"))


class CompleteCommand(unittest.TestCase):
    """`complete habit <name>` as the console runs it (commands/complete.py)."""

    def test_it_records_the_habit_and_todays_completion_log(self):
        with temporary_kairos_user_fixture() as fixture:
            user_dir = fixture["user_dir"]
            _write(user_dir, "habits/stretch.yml", STRETCH)
            _quiet(Complete.run, ["habit", "Stretch"], {})
            self.assertIn(TODAY, read_item_data("habit", "Stretch").get("completion_dates") or [])
            with open(os.path.join(user_dir, "schedules", "completions", f"{TODAY}.yml"), encoding="utf-8") as fh:
                entries = (yaml.safe_load(fh) or {}).get("entries") or {}
            statuses = {str(e.get("name")): str(e.get("status")) for e in entries.values() if isinstance(e, dict)}
            self.assertEqual(statuses.get("Stretch"), "completed")

    def test_kairos_does_not_plan_it_again_today(self):
        with temporary_kairos_user_fixture() as fixture:
            _write(fixture["user_dir"], "habits/stretch.yml", STRETCH)
            _quiet(Complete.run, ["habit", "Stretch"], {})
            now = datetime.now()
            with contextlib.redirect_stdout(io.StringIO()):
                schedule = KairosV2Scheduler({"now": now, "start_from_now": True}).generate_schedule(now.date())
            impossible = {
                row.get("name"): row.get("impossible_reason")
                for row in schedule.get("schedule", {}).get("reality_filtered_candidates", {}).get("impossible_candidates", [])
            }
            self.assertEqual(impossible.get("Stretch"), "already_completed_today")


class TrackHabit(unittest.TestCase):
    def _track(self, habit):
        with temporary_kairos_user_fixture() as fixture:
            if habit:
                _write(fixture["user_dir"], f"habits/{habit['name'].lower()}.yml", habit)
            return _quiet(dispatch_command, "track", "habit", (habit or {}).get("name", "Nope"), None, {})

    def test_a_good_habit_shows_its_streaks(self):
        out = self._track({**STRETCH, "current_streak": 2, "longest_streak": 5})
        self.assertIn("Current Streak: 2", out)
        self.assertIn("Longest Streak: 5", out)

    def test_a_bad_habit_shows_its_last_incident(self):
        out = self._track({"name": "Doomscroll", "type": "habit", "polarity": "bad", "last_incident": _days_ago(2)})
        self.assertIn("Polarity: bad (avoid)", out)
        self.assertIn(f"Last Incident: {_days_ago(2)}", out)

    def test_an_unknown_habit_is_reported(self):
        self.assertIn("not found", self._track(None))


class DeleteHabit(unittest.TestCase):
    def test_delete_with_force_removes_it(self):
        with temporary_kairos_user_fixture() as fixture:
            _write(fixture["user_dir"], "habits/stretch.yml", STRETCH)
            _quiet(dispatch_command, "delete", "habit", "Stretch", None, {"force": True})
            self.assertFalse(read_item_data("habit", "Stretch"))


if __name__ == "__main__":
    unittest.main()
