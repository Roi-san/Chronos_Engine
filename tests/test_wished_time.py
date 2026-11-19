"""
An item's own time is a wish (decision D7, 2026-11-19; issue 42;
`docs/scheduling/planning_and_tracking_model.md`, proposal C).

A habit, routine, task or chore with its own `start_time` (the builders write
`ideal_start_time`, normalised to `start_time`) is planned at that time when the
time is free: no fixed block, timed block, window or sleep there, not past, not
running into bedtime. Otherwise it is planned like any other item, in free time,
and the plan says why (`schedule.wished_times`, Home's plan notes). Fixed things
stay fixed: anchors, the day template's timed blocks, and (pilot, 2026-11-19)
appointments, which must be locked in place (issue 17, not built yet).

Before: every item's own time was ignored. A daily "Meditate" at 21:00 was planned
at 08:35, the first free gap.

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
from modules.scheduler.kairos_v2 import KairosV2Scheduler  # noqa: E402
from test_kairos_v2_direction import _seed, _write  # noqa: E402
from utilities.dashboard import home_api  # noqa: E402

NOW = datetime(2026, 4, 16, 8, 0)


def fixed(name, start, end):
    return {"name": name, "type": "timeblock", "start_time": start, "end_time": end, "reschedule": "never"}


SLEEP = {**fixed("Core Sleep", "23:30", "07:30"), "category": "sleep"}
DAY = {"name": "My Day", "type": "day", "children": [
    SLEEP, fixed("Breakfast", "08:00", "08:30"), fixed("Work", "09:00", "17:00"), fixed("Dinner", "18:30", "19:00"),
]}


def habit(name, minutes, **extra):
    return {"name": name, "type": "habit", "duration": minutes, "frequency": "daily", **extra}


def plan(files, now=NOW, template=DAY, from_now=False):
    with temporary_kairos_user_fixture() as fixture:
        user = fixture["user_dir"]
        for name in os.listdir(os.path.join(user, "days")):
            os.remove(os.path.join(user, "days", name))
        _write(os.path.join(user, "days", "my_day.yml"), template)
        _seed(user, files)
        with redirect_stdout(io.StringIO()):
            # `today` / Home plan from now (start_from_now), as the real command does.
            context = {"now": now, "start_from_now": True} if from_now else {"now": now}
            result = KairosV2Scheduler(context).generate_schedule(now.date())
    return result.get("schedule", {})


def where(schedule, name):
    found = []

    def walk(blocks):
        for block in blocks or []:
            if str(block.get("name")) == name and not block.get("children"):
                found.append(f"{block.get('start_time')}-{block.get('end_time')}")
            walk(block.get("children"))

    walk(schedule.get("conceptual_schedule", {}).get("conceptual_blocks"))
    return found


def wish(schedule, name):
    rows = [row for row in schedule.get("wished_times") or [] if row.get("name") == name]
    return rows[0] if rows else None


class AtItsTime(unittest.TestCase):
    def test_a_habit_at_2100(self):
        s = plan({"habits/meditate.yml": habit("Meditate", 15, start_time="21:00")})
        self.assertEqual(where(s, "Meditate"), ["21:00-21:15"])
        self.assertTrue(wish(s, "Meditate")["placed"])

    def test_the_builders_field(self):
        s = plan({"habits/meditate.yml": habit("Meditate", 15, ideal_start_time="21:00")})
        self.assertEqual(where(s, "Meditate"), ["21:00-21:15"])

    def test_a_routine_with_a_frequency_and_a_time(self):
        routine = {"name": "Evening Wind-down", "type": "routine", "frequency": "daily", "start_time": "22:30",
                   "children": [{"type": "habit", "name": "Stretch", "duration": 10},
                                {"type": "habit", "name": "Journal", "duration": 15}]}
        s = plan({"routines/wind.yml": routine,
                  "habits/stretch.yml": {"name": "Stretch", "type": "habit", "duration": 10},
                  "habits/journal.yml": {"name": "Journal", "type": "habit", "duration": 15}})
        self.assertEqual(where(s, "Evening Wind-down"), ["22:30-22:55"])

    def test_items_without_a_time_are_not_listed(self):
        s = plan({"habits/read.yml": habit("Read", 30)})
        self.assertEqual(s.get("wished_times"), [])


class WhenTheTimeIsNotFree(unittest.TestCase):
    def test_taken_by_a_fixed_block_it_moves_and_says_why(self):
        s = plan({"habits/meditate.yml": habit("Meditate", 15, start_time="18:45")})
        row = wish(s, "Meditate")
        self.assertFalse(row["placed"])
        self.assertIn("Dinner", row["why"])
        placed = where(s, "Meditate")
        self.assertEqual(len(placed), 1)
        self.assertNotEqual(placed[0], "18:45-19:00")

    def test_two_wishes_for_the_same_time(self):
        s = plan({"habits/a.yml": habit("Meditate", 15, start_time="21:00", priority="high"),
                  "habits/b.yml": habit("Stretch", 15, start_time="21:00")})
        placed = [name for name in ("Meditate", "Stretch") if wish(s, name)["placed"]]
        self.assertEqual(len(placed), 1)
        other = "Stretch" if placed == ["Meditate"] else "Meditate"
        self.assertIn(placed[0], wish(s, other)["why"])
        self.assertEqual(len(where(s, other)), 1)          # still planned, elsewhere

    def test_a_time_already_past_today(self):
        # 19:15 is free (after Dinner); at 20:00, planning from now, it has passed.
        s = plan({"habits/meditate.yml": habit("Meditate", 15, start_time="19:15")}, now=datetime(2026, 4, 16, 20, 0), from_now=True)
        row = wish(s, "Meditate")
        self.assertFalse(row["placed"])
        self.assertIn("passed", row["why"])
        self.assertEqual(len(where(s, "Meditate")), 1)

    def test_running_into_bedtime(self):
        s = plan({"habits/meditate.yml": habit("Meditate", 30, start_time="23:15")})
        row = wish(s, "Meditate")
        self.assertFalse(row["placed"])
        self.assertIn("bedtime", row["why"])

    def test_not_its_day_means_not_planned_at_all(self):
        # A weekly chore whose turn is Saturday is not on Thursday's plan, time or not.
        chore = {"name": "Laundry", "type": "habit", "duration": 60, "frequency": "weekly", "day": "saturday",
                 "start_time": "10:00", "created": "2026-01-01"}
        s = plan({"habits/laundry.yml": chore})
        self.assertEqual(where(s, "Laundry"), [])
        self.assertIsNone(wish(s, "Laundry"))


class HomeSaysWhy(unittest.TestCase):
    def test_a_moved_wish_is_a_plan_note(self):
        meta = {"wished_times": [
            {"name": "Meditate", "wished": "18:45", "placed": False, "why": "Dinner is at that time"},
            {"name": "Read", "wished": "21:00", "placed": True, "why": "the time was free"},
        ]}
        notes = home_api.plan_notes(meta)
        self.assertEqual(len(notes), 1)
        self.assertIn("Meditate", notes[0])
        self.assertIn("18:45", notes[0])
        self.assertIn("Dinner", notes[0])


if __name__ == "__main__":
    unittest.main()
