"""
What counts as sleep (decision D5, 2026-11-19; issues 38, 43, 46).

`docs/scheduling/planning_and_tracking_model.md`, proposal A: only a block on a
day template can be sleep, marked as sleep by the wizard that made it
(`sleep: true`, category or tag `sleep`). Habits, routines, microroutines and
tasks are ordinary work whatever their name or marks. A day with no marked
block falls back to a fixed timeblock whose name contains "sleep" (old and
hand-written templates), and the plan records that it did.

Before:
- #38: any item named "...bedtime..." or "...sleep..." was treated as sleep and
  left out: a "Bedtime Routine" was never planned; anchored at 22:30 it became
  the end of the day and vanished.
- #43: the Sleep Settings wizard's wind-down pack (microroutines marked
  `sleep: true`) was never planned.
- #46: the sleep blocks the Sleep Settings widget writes (`sleep: true`, no
  `reschedule: never`) were not sleep for Kairos: the plan ran to 23:59.

Fixture clock: Thursday 16 April 2026, 08:00.
"""
import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from chronos_fixture import temporary_kairos_user_fixture  # noqa: E402
from modules.scheduler import sleep_blocks as SleepBlocks  # noqa: E402
from modules.scheduler import sleep_gate as SleepGate  # noqa: E402
from modules.scheduler.kairos_v2 import KairosV2Scheduler  # noqa: E402
from test_kairos_v2_direction import _seed, _write  # noqa: E402

NOW = datetime(2026, 4, 16, 8, 0)

# What Life Setup writes (the pilot's own template has exactly these marks).
LIFE_SETUP_SLEEP = {"name": "Core Sleep", "type": "timeblock", "start_time": "23:30", "end_time": "07:30",
                    "duration": 480, "reschedule": "never", "essential": True,
                    "category": "sleep", "tags": ["anchor", "sleep"]}
# What the Sleep Settings widget writes (server.py): marked, but no `reschedule: never`.
SLEEP_SETTINGS_SLEEP = {"name": "Core Sleep", "type": "timeblock", "start_time": "23:00", "end_time": "07:00",
                        "tags": ["anchor", "sleep"], "category": "sleep", "sleep": True}
# An old or hand-written template: fixed, named, not marked.
UNMARKED_SLEEP = {"name": "Sleep", "type": "timeblock", "start_time": "23:30", "end_time": "07:30",
                  "duration": 480, "reschedule": "never"}
WORK = {"name": "Work", "type": "timeblock", "start_time": "09:00", "end_time": "17:00", "reschedule": "never"}

STEPS = [{"type": "habit", "name": "Brush teeth", "duration": 5},
         {"type": "habit", "name": "Read a book", "duration": 20}]
STEP_FILES = {"habits/brush.yml": {"name": "Brush teeth", "type": "habit", "duration": 5},
              "habits/read.yml": {"name": "Read a book", "type": "habit", "duration": 20}}
# What the Sleep Settings wizard creates (sleep_settings/index.js), plus a frequency.
WIND_DOWN_PACK = {"name": "Sleep Hygiene - Digital Sunset", "type": "microroutine", "duration": 15,
                  "category": "sleep", "sleep": True, "tags": ["sleep", "hygiene", "bedtime"], "frequency": "daily"}


def bedtime_routine(**extra):
    return {"name": "Bedtime Routine", "type": "routine", "category": "sleep", "sleep": True,
            "tags": ["sleep", "bedtime"], "children": STEPS, **extra}


def day(*children):
    return {"name": "My Day", "type": "day", "children": list(children)}


def plan(template, files=None, now=NOW):
    with temporary_kairos_user_fixture() as fixture:
        user = fixture["user_dir"]
        for name in os.listdir(os.path.join(user, "days")):
            os.remove(os.path.join(user, "days", name))
        _write(os.path.join(user, "days", "my_day.yml"), template)
        _seed(user, {**STEP_FILES, **(files or {})})
        with redirect_stdout(io.StringIO()):
            result = KairosV2Scheduler({"now": now}).generate_schedule(now.date())
    return result.get("schedule", {})


def where(schedule, name):
    found = []

    def walk(blocks):
        for block in blocks or []:
            if str(block.get("name")) == name:
                found.append(f"{block.get('start_time')}-{block.get('end_time')}")
            walk(block.get("children"))

    walk(schedule.get("conceptual_schedule", {}).get("conceptual_blocks"))
    return found


def plan_ends(schedule):
    budget = schedule.get("day_budget") or {}
    return budget.get("sleep_boundary_time"), budget.get("sleep_boundary_source")


class TheRule(unittest.TestCase):
    def test_blocks_marked_by_the_wizards_are_sleep(self):
        self.assertTrue(SleepBlocks.is_marked_sleep_block(LIFE_SETUP_SLEEP))
        self.assertTrue(SleepBlocks.is_marked_sleep_block(SLEEP_SETTINGS_SLEEP))

    def test_work_items_are_never_sleep_whatever_their_name_or_marks(self):
        for item in (bedtime_routine(), WIND_DOWN_PACK,
                     {"name": "Sleep 8 hours", "type": "habit", "category": "sleep"},
                     {"name": "Bedtime", "type": "task", "sleep": True}):
            self.assertFalse(SleepBlocks.is_marked_sleep_block(item), item["name"])
            self.assertEqual(SleepBlocks.template_sleep_blocks([{**item, "reschedule": "never"}]), [], item["name"])

    def test_the_name_counts_only_on_a_day_with_no_marked_block(self):
        clinic = {"name": "Sleep clinic", "type": "timeblock", "start_time": "15:00", "end_time": "16:00", "reschedule": "never"}
        self.assertEqual(SleepBlocks.template_sleep_blocks([UNMARKED_SLEEP, WORK]), [UNMARKED_SLEEP])
        self.assertTrue(SleepBlocks.uses_name_fallback([UNMARKED_SLEEP, WORK]))
        self.assertEqual(SleepBlocks.template_sleep_blocks([LIFE_SETUP_SLEEP, clinic]), [LIFE_SETUP_SLEEP])
        self.assertFalse(SleepBlocks.uses_name_fallback([LIFE_SETUP_SLEEP, clinic]))
        # Not fixed, not marked: never sleep.
        self.assertEqual(SleepBlocks.template_sleep_blocks([{**UNMARKED_SLEEP, "reschedule": "auto"}]), [])


class BedtimeRoutinesArePlanned(unittest.TestCase):
    def test_on_the_day_at_2230(self):
        s = plan(day(LIFE_SETUP_SLEEP, WORK, {"type": "routine", "name": "Bedtime Routine", "ideal_start_time": "22:30"}),
                 {"routines/bedtime.yml": bedtime_routine()})
        self.assertEqual(where(s, "Bedtime Routine"), ["22:30-22:55"])
        self.assertEqual(plan_ends(s)[0], "23:30")

    def test_from_the_library_with_a_frequency(self):
        s = plan(day(LIFE_SETUP_SLEEP, WORK), {"routines/bedtime.yml": bedtime_routine(frequency="daily")})
        self.assertEqual(len(where(s, "Bedtime Routine")), 1)

    def test_the_sleep_settings_wind_down_pack(self):
        s = plan(day(LIFE_SETUP_SLEEP, WORK), {"microroutines/sunset.yml": WIND_DOWN_PACK})
        self.assertEqual(len(where(s, "Sleep Hygiene - Digital Sunset")), 1)

    def test_anchored_it_is_a_fixed_block_and_sleep_still_starts_at_2330(self):
        anchored = {"type": "routine", "name": "Bedtime Routine", "start_time": "22:30", "end_time": "23:00",
                    "reschedule": "never", "sleep": True, "category": "sleep"}
        s = plan(day(LIFE_SETUP_SLEEP, WORK, anchored), {"routines/bedtime.yml": bedtime_routine()})
        self.assertEqual(plan_ends(s)[0], "23:30")
        self.assertEqual(where(s, "Bedtime Routine"), ["22:30-23:00"])


class SleepBlocksAreSleep(unittest.TestCase):
    def test_life_setup_block(self):
        s = plan(day(LIFE_SETUP_SLEEP, WORK))
        self.assertEqual(plan_ends(s), ("23:30", "sleep_anchor"))
        self.assertEqual(s["sleep_blocks"]["names"], ["Core Sleep"])
        self.assertFalse(s["sleep_blocks"]["by_name"])

    def test_sleep_settings_block_without_reschedule_never(self):
        s = plan(day(SLEEP_SETTINGS_SLEEP, WORK))
        self.assertEqual(plan_ends(s), ("23:00", "sleep_anchor"))
        self.assertEqual(where(s, "Core Sleep"), [])
        names = [c.get("name") for c in s.get("candidate_universe", {}).get("candidates", [])]
        self.assertNotIn("Core Sleep", names)

    def test_old_unmarked_template_keeps_working_and_says_so(self):
        s = plan(day(UNMARKED_SLEEP, WORK))
        self.assertEqual(plan_ends(s), ("23:30", "sleep_anchor"))
        self.assertTrue(s["sleep_blocks"]["by_name"])
        self.assertEqual(s["sleep_blocks"]["names"], ["Sleep"])

    def test_a_fixed_block_with_sleep_in_its_name_beside_a_marked_one_is_not_sleep(self):
        clinic = {"name": "Sleep clinic", "type": "timeblock", "start_time": "15:00", "end_time": "16:00", "reschedule": "never"}
        s = plan(day(LIFE_SETUP_SLEEP, WORK, clinic))
        self.assertEqual(plan_ends(s)[0], "23:30")
        self.assertEqual(s["sleep_blocks"]["names"], ["Core Sleep"])


class SleepLogAndGate(unittest.TestCase):
    def test_a_finished_bedtime_routine_is_not_counted_as_sleep(self):
        entries = {"entries": {
            "Bedtime Routine@22:30": {"name": "Bedtime Routine", "status": "completed", "duration": 30},
            "Core Sleep@23:30": {"name": "Core Sleep", "status": "completed", "duration": 480},
        }}
        with temporary_kairos_user_fixture() as fixture:
            user = fixture["user_dir"]
            for name in os.listdir(os.path.join(user, "days")):
                os.remove(os.path.join(user, "days", name))
            _write(os.path.join(user, "days", "my_day.yml"), day(LIFE_SETUP_SLEEP, WORK))
            _write(os.path.join(user, "schedules", "completions", "2026-04-15.yml"), entries)
            minutes = KairosV2Scheduler({"now": NOW})._read_sleep_minutes_from_completion_file(datetime(2026, 4, 15).date())
        self.assertEqual(minutes, 480)

    def test_the_sleep_question_is_not_asked_during_a_bedtime_routine(self):
        anchored = {"type": "routine", "name": "Bedtime Routine", "start_time": "22:30", "end_time": "23:05",
                    "reschedule": "never", "sleep": True, "category": "sleep"}
        with temporary_kairos_user_fixture() as fixture:
            user = fixture["user_dir"]
            for name in os.listdir(os.path.join(user, "days")):
                os.remove(os.path.join(user, "days", name))
            _write(os.path.join(user, "days", "my_day.yml"), day(LIFE_SETUP_SLEEP, WORK, anchored))
            during_routine = SleepGate.get_active_sleep_block(now=datetime(2026, 4, 16, 22, 40))
            during_sleep = SleepGate.get_active_sleep_block(now=datetime(2026, 4, 16, 23, 45))
        self.assertIsNone(during_routine)
        self.assertEqual(during_sleep["name"], "Core Sleep")


if __name__ == "__main__":
    unittest.main()
