"""
Where Kairos v2 ends (and starts) the plannable day.

Issue #1 in docs/ISSUES_AND_NEXT_STEPS.md: a sleep block that starts after
midnight (02:00, 00:30) was read as starting *this morning*, so Kairos thought
the day was already over and placed no flexible work all day. The pilot's real
Life Skeleton (Core Sleep 02:00-10:30) hit this on every re-plan.

Decisions (pilot, 2026-11-18), full write-up in
docs/scheduling/sleep_after_midnight.md:
- A sleep block that starts between 00:00 and 11:59 is a bedtime after midnight:
  it belongs to the night *after* the day.
- The plan stops at 23:59, the end of the calendar day, never later (all of
  Chronos reads 00:00 as the start of a day).
- After midnight but before that bedtime, the plan runs until the bedtime.
- Several sleep blocks: the soonest upcoming bedtime ends the plan.
- No sleep block at all: the plan runs until 23:59 (it used to stop at 16:00).
- "Go back to sleep" / "Shift today later" plan from the wake-up time (they used
  to plan nothing flexible at all).
"""
import io
import os
import sys
import unittest
from contextlib import ExitStack, redirect_stdout
from datetime import datetime
from unittest.mock import patch

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from chronos_fixture import temporary_kairos_user_fixture
from modules.scheduler.kairos_v2 import KairosV2Scheduler
from modules.scheduler.runtime import build_day_runtime_payload, get_flattened_runtime_items
from test_kairos_v2_direction import _seed, _write

END_OF_DAY = 23 * 60 + 59  # 23:59


def at(hour, minute=0):
    """A clock time on the fixture's day, Thursday 16 April 2026."""
    return datetime(2026, 4, 16, hour, minute)


def _sleep(start, end=None, duration=None, name="Core Sleep"):
    node = {"name": name, "type": "timeblock", "start_time": start, "reschedule": "never", "category": "sleep"}
    if end is not None:
        node["end_time"] = end
    if duration is not None:
        node["duration"] = duration
    return node


def _anchor(name, start, end, minutes):
    return {"name": name, "type": "timeblock", "start_time": start, "end_time": end,
            "duration": minutes, "reschedule": "never"}


def _day(*sleep_blocks):
    children = list(sleep_blocks) + [
        _anchor("Breakfast", "11:00", "11:15", 15),
        _anchor("Work", "12:00", "15:00", 180),
        _anchor("Dinner", "21:00", "21:30", 30),
    ]
    return {"name": "Night Owl Day", "type": "day", "children": children}


# The shape of the pilot's real Life Skeleton (times only).
NIGHT_OWL_DAY = _day(_sleep("02:00", "10:30", 510))
EVENING_DAY = _day(_sleep("23:30", "07:30", 480))
NO_SLEEP_DAY = _day()

# 90 minutes of flexible work (plus the base fixture's 10-minute "Stretch Break").
FLEXIBLE = {"Read a chapter", "Evening stretch", "Journal"}


def _library(day):
    return {
        "tasks/read.yml": {"name": "Read a chapter", "type": "task", "duration": "45m", "due_date": day.isoformat()},
        "habits/stretch.yml": {"name": "Evening stretch", "type": "habit", "duration": "20m", "frequency": "daily"},
        "habits/journal.yml": {"name": "Journal", "type": "habit", "duration": "15m", "frequency": "daily"},
    }


def _install_day(user_dir, day, now):
    days_dir = os.path.join(user_dir, "days")
    for name in os.listdir(days_dir):
        os.remove(os.path.join(days_dir, name))
    if day is not None:
        _write(os.path.join(days_dir, "day.yml"), day)
    _seed(user_dir, _library(now.date()))


def _result(day, now, remaining=True, **context):
    """Run Kairos at `now`. remaining=True is what `today reschedule` (Home's Re-plan) does."""
    if remaining:
        context["start_from_now"] = True
    with temporary_kairos_user_fixture() as fixture:
        _install_day(fixture["user_dir"], day, now)
        return KairosV2Scheduler({"now": now, **context}).generate_schedule(now.date())


def _plan(day, now, remaining=True, **context):
    return _result(day, now, remaining, **context).get("schedule", {})


def _placed(schedule):
    """Every placed item that is not an anchor, flattened out of the conceptual blocks."""
    rows = []
    for block in schedule.get("conceptual_schedule", {}).get("conceptual_blocks", []):
        children = block.get("children") or []
        if children:
            rows.extend(child for child in children if isinstance(child, dict))
        elif block.get("kind") != "anchor":
            rows.append(block)
    return rows


def _names(schedule):
    return {row.get("name") for row in _placed(schedule)}


class BedtimeAfterMidnight(unittest.TestCase):
    """The pilot's shape: Core Sleep 02:00-10:30."""

    def test_a_daytime_replan_plans_flexible_work(self):
        schedule = _plan(NIGHT_OWL_DAY, at(11, 0))
        self.assertTrue(FLEXIBLE <= _names(schedule), _names(schedule))

    def test_an_evening_replan_fills_the_evening(self):
        schedule = _plan(NIGHT_OWL_DAY, at(22, 0))
        self.assertTrue(FLEXIBLE <= _names(schedule), _names(schedule))

    def test_nothing_is_placed_past_the_end_of_the_calendar_day(self):
        rows = _placed(_plan(NIGHT_OWL_DAY, at(22, 0)))
        self.assertTrue(rows)
        for row in rows:
            self.assertGreaterEqual(row["start_minutes"], 22 * 60, row)
            self.assertLessEqual(row["end_minutes"], END_OF_DAY, row)

    def test_the_plan_stops_at_2359_and_records_the_real_bedtime(self):
        budget = _plan(NIGHT_OWL_DAY, at(22, 0))["day_budget"]
        self.assertEqual(budget["sleep_boundary_time"], "23:59")
        self.assertEqual(budget["sleep_boundary_minutes"], END_OF_DAY)
        self.assertEqual(budget["sleep_boundary_source"], "sleep_anchor_after_midnight")
        self.assertEqual(budget["remaining_minutes_before_sleep"], 119)
        self.assertEqual(budget["bedtime_time"], "02:00")
        self.assertEqual(budget["bedtime_day"], "tomorrow")
        self.assertEqual(budget["bedtime_minutes"], 24 * 60 + 120)
        self.assertEqual(budget["bedtime_anchor"], "Core Sleep")

    def test_after_midnight_but_before_bed_the_plan_runs_until_bedtime(self):
        schedule = _plan(NIGHT_OWL_DAY, at(0, 30))
        budget = schedule["day_budget"]
        self.assertEqual(budget["sleep_boundary_time"], "02:00")
        self.assertEqual(budget["sleep_boundary_source"], "sleep_anchor")
        self.assertEqual(budget["bedtime_day"], "today")
        rows = _placed(schedule)
        self.assertTrue(FLEXIBLE <= {row["name"] for row in rows})
        for row in rows:
            self.assertGreaterEqual(row["start_minutes"], 30, row)
            self.assertLessEqual(row["end_minutes"], 120, row)

    def test_awake_inside_the_sleep_block_and_staying_up_plans_the_day_from_now(self):
        rows = _placed(_plan(NIGHT_OWL_DAY, at(3, 0), sleep_policy="stay_awake"))
        self.assertTrue(FLEXIBLE <= {row["name"] for row in rows})
        self.assertGreaterEqual(min(row["start_minutes"] for row in rows), 3 * 60)

    def test_going_back_to_sleep_plans_the_day_from_wake_up(self):
        rows = _placed(_plan(NIGHT_OWL_DAY, at(3, 0), sleep_policy="go_back_to_sleep"))
        self.assertTrue(FLEXIBLE <= {row["name"] for row in rows})
        self.assertGreaterEqual(min(row["start_minutes"] for row in rows), 10 * 60 + 30)

    def test_a_full_day_run_without_start_from_now_also_fills_the_evening(self):
        schedule = _plan(NIGHT_OWL_DAY, at(22, 0), remaining=False)
        self.assertTrue(FLEXIBLE <= _names(schedule), _names(schedule))

    def test_the_decision_log_notes_name_the_bedtime(self):
        notes = _result(NIGHT_OWL_DAY, at(22, 0))["phase_notes"]["model_day_budget"]
        self.assertEqual(notes["sleep_boundary_time"], "23:59")
        self.assertEqual(notes["sleep_boundary_source"], "sleep_anchor_after_midnight")
        self.assertEqual((notes["bedtime_time"], notes["bedtime_day"]), ("02:00", "tomorrow"))


class OtherBedtimesAfterMidnight(unittest.TestCase):
    def test_sleep_at_0030_given_only_a_duration(self):
        # The case found on 2026-11-17 (step 3 end-to-end test).
        day = _day({**_sleep("00:30", duration=450, name="Sleep"), "sleep": True})
        schedule = _plan(day, at(22, 4))
        self.assertTrue(FLEXIBLE <= _names(schedule), _names(schedule))
        self.assertEqual(schedule["day_budget"]["bedtime_time"], "00:30")

    def test_bedtime_exactly_at_midnight(self):
        schedule = _plan(_day(_sleep("00:00", "08:00", 480)), at(20, 0))
        self.assertTrue(FLEXIBLE <= _names(schedule), _names(schedule))
        self.assertEqual(schedule["day_budget"]["sleep_boundary_time"], "23:59")

    def test_a_bedtime_with_no_end_and_no_duration(self):
        schedule = _plan(_day(_sleep("01:00")), at(22, 0))
        self.assertTrue(FLEXIBLE <= _names(schedule), _names(schedule))
        self.assertEqual(schedule["day_budget"]["bedtime_day"], "tomorrow")

    def test_a_very_late_sleeper_who_is_still_up_goes_to_bed_today(self):
        budget = _plan(_day(_sleep("05:00", "13:00", 480)), at(3, 0))["day_budget"]
        self.assertEqual((budget["sleep_boundary_time"], budget["bedtime_day"]), ("05:00", "today"))
        self.assertEqual(budget["remaining_minutes_before_sleep"], 120)


class SeveralSleepBlocks(unittest.TestCase):
    """The Sleep wizard writes Core Sleep plus a later 'Sleep In' on weekend templates."""

    DAY = _day(_sleep("23:30", "07:30", 480), _sleep("00:30", "09:30", 540, name="Sleep In"))

    def test_in_the_evening_the_earlier_bedtime_wins(self):
        budget = _plan(self.DAY, at(22, 0))["day_budget"]
        self.assertEqual((budget["sleep_boundary_time"], budget["bedtime_anchor"]), ("23:30", "Core Sleep"))

    def test_after_midnight_the_bedtime_still_ahead_wins(self):
        budget = _plan(self.DAY, at(0, 10))["day_budget"]
        self.assertEqual((budget["sleep_boundary_time"], budget["bedtime_anchor"]), ("00:30", "Sleep In"))
        self.assertEqual(budget["bedtime_day"], "today")


class EveningBedtimeUnchanged(unittest.TestCase):
    """A bedtime before midnight already worked and must plan exactly as before."""

    def test_the_day_still_ends_at_an_evening_bedtime(self):
        budget = _plan(EVENING_DAY, at(22, 0))["day_budget"]
        self.assertEqual(budget["sleep_boundary_time"], "23:30")
        self.assertEqual(budget["sleep_boundary_source"], "sleep_anchor")
        self.assertEqual(budget["remaining_minutes_before_sleep"], 90)
        self.assertEqual((budget["bedtime_time"], budget["bedtime_day"]), ("23:30", "today"))

    def test_nothing_is_placed_after_an_evening_bedtime(self):
        rows = _placed(_plan(EVENING_DAY, at(22, 0)))
        self.assertTrue(rows)
        for row in rows:
            self.assertLessEqual(row["end_minutes"], 23 * 60 + 30, row)

    def test_a_sleep_block_starting_in_the_afternoon_is_still_today(self):
        # A night-shift sleep, 13:00-21:00: noon and later is never "after midnight".
        budget = _plan(_day(_sleep("13:00", "21:00", 480)), at(9, 0))["day_budget"]
        self.assertEqual((budget["sleep_boundary_time"], budget["bedtime_day"]), ("13:00", "today"))

    def test_inside_an_evening_sleep_block_with_no_answer_nothing_new_is_planned(self):
        schedule = _plan(EVENING_DAY, at(23, 45))
        self.assertEqual(schedule["day_budget"]["remaining_minutes_before_sleep"], 0)
        self.assertFalse(_names(schedule) & FLEXIBLE)


class SleepPromptAnswers(unittest.TestCase):
    """The answers to "You're inside a scheduled sleep block" (modules/scheduler/sleep_gate.py)."""

    def test_go_back_to_sleep_plans_from_wake_up_for_an_evening_sleeper(self):
        rows = _placed(_plan(EVENING_DAY, at(3, 0), sleep_policy="go_back_to_sleep"))
        self.assertTrue(FLEXIBLE <= {row["name"] for row in rows})
        self.assertGreaterEqual(min(row["start_minutes"] for row in rows), 7 * 60 + 30)

    def test_shift_today_later_plans_from_wake_up(self):
        rows = _placed(_plan(EVENING_DAY, at(3, 0), sleep_policy="shift_later"))
        self.assertTrue(FLEXIBLE <= {row["name"] for row in rows})
        self.assertGreaterEqual(min(row["start_minutes"] for row in rows), 7 * 60 + 30)

    def test_stay_awake_still_plans_from_now(self):
        rows = _placed(_plan(EVENING_DAY, at(3, 0), sleep_policy="stay_awake"))
        self.assertTrue(FLEXIBLE <= {row["name"] for row in rows})
        self.assertEqual(min(row["start_minutes"] for row in rows), 3 * 60)


class NoSleepBlock(unittest.TestCase):
    """No bedtime known: plan until 23:59 (it used to stop at 16:00, 24h minus 8h of sleep)."""

    def test_an_evening_replan_fills_the_evening(self):
        schedule = _plan(NO_SLEEP_DAY, at(22, 0))
        self.assertTrue(FLEXIBLE <= _names(schedule), _names(schedule))
        budget = schedule["day_budget"]
        self.assertEqual(budget["sleep_boundary_time"], "23:59")
        self.assertEqual(budget["sleep_boundary_source"], "no_sleep_anchor")
        self.assertIsNone(budget["bedtime_time"])
        self.assertIsNone(budget["bedtime_day"])

    def test_the_day_is_not_cut_off_at_1600(self):
        gaps = _plan(NO_SLEEP_DAY, at(11, 0))["gap_buffer_recovery"]["emergent_gaps"]
        self.assertEqual(max(gap["end_minutes"] for gap in gaps), END_OF_DAY)

    def test_no_day_template_at_all(self):
        # A brand-new user's first day.
        schedule = _plan(None, at(22, 0))
        self.assertTrue(FLEXIBLE <= _names(schedule), _names(schedule))
        self.assertEqual(schedule["day_budget"]["sleep_boundary_source"], "no_sleep_anchor")


class TheScheduleFileHomeReads(unittest.TestCase):
    """The plan reaches the schedule file (modules/scheduler/runtime.py) with sane times."""

    def test_the_evening_plan_is_in_the_runtime_payload(self):
        result = _result(NIGHT_OWL_DAY, at(22, 0))
        items = get_flattened_runtime_items(build_day_runtime_payload(at(22, 0).date(), result))
        self.assertTrue(FLEXIBLE <= {item.get("name") for item in items})
        for item in items:
            if item.get("start_minutes") is None:
                continue
            self.assertGreaterEqual(item["start_minutes"], 22 * 60, item)
            self.assertLessEqual(item["end_minutes"], END_OF_DAY, item)

    def test_today_reschedule_writes_the_evening_plan(self):
        from commands import today as Today
        from modules.scheduler import load_day_runtime, schedule_path_for_date

        now = at(22, 0)

        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(now.year, now.month, now.day, now.hour, now.minute)

        def scheduler(user_context=None):
            return KairosV2Scheduler({**(user_context or {}), "now": now})

        with ExitStack() as stack:
            fixture = stack.enter_context(temporary_kairos_user_fixture())
            _install_day(fixture["user_dir"], NIGHT_OWL_DAY, now)
            stack.enter_context(patch("modules.scheduler.KairosV2Scheduler", side_effect=scheduler))
            stack.enter_context(patch("commands.today.datetime", Clock))
            stack.enter_context(patch("commands.today.build_sleep_interrupt", return_value=None))
            with redirect_stdout(io.StringIO()):
                Today.run(["reschedule"], {})
            date_str = now.strftime("%Y-%m-%d")
            payload = load_day_runtime(date_str, path=schedule_path_for_date(date_str))
        names = {item.get("name") for item in get_flattened_runtime_items(payload)}
        self.assertTrue(FLEXIBLE <= names, names)


if __name__ == "__main__":
    unittest.main()
