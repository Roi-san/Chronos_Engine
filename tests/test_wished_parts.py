"""
Parts of the day as a wish (decision D8, 2026-11-19; proposal C in
`docs/scheduling/planning_and_tracking_model.md`).

An item can say *when* without a clock time: `when: morning`, `afternoon`,
`evening` or `before bed` (`when: "21:00"` is a clock time, like `start_time`).
Morning runs from waking up (the end of the day's sleep block, 07:00 without one)
to 12:00, afternoon 12:00-17:00, evening 17:00 to bedtime, and "before bed" is
the last two hours before bedtime (where the plan ends). A morning, afternoon or
evening item takes the first free stretch of its part; a "before bed" item the
last one, so it ends as close to bedtime as possible. When its part has no free
stretch (or has passed), it is planned like any other item and the plan says why.
The pilot (2026-11-19) answered D8 "the most intuitive answer": "before bed" is a
part of its own.

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

from modules.scheduler import day_parts as DayParts  # noqa: E402
from test_wished_time import DAY, habit, plan, where, wish  # noqa: E402
from utilities.dashboard import home_api  # noqa: E402

NOW = datetime(2026, 4, 16, 8, 0)


class TheParts(unittest.TestCase):
    def test_reading_when(self):
        self.assertEqual(DayParts.parse_when("evening"), ("part", "evening"))
        self.assertEqual(DayParts.parse_when("Before bed"), ("part", "before_bed"))
        self.assertEqual(DayParts.parse_when("before_bed"), ("part", "before_bed"))
        self.assertEqual(DayParts.parse_when("21:00"), ("time", 21 * 60))
        self.assertEqual(DayParts.parse_when("sometime"), ("unknown", "sometime"))
        self.assertIsNone(DayParts.parse_when(""))
        self.assertIsNone(DayParts.parse_when(None))

    def test_windows_follow_waking_and_bedtime(self):
        self.assertEqual(DayParts.window("morning", wake=450, bed=1410), (450, 720))
        self.assertEqual(DayParts.window("afternoon", wake=450, bed=1410), (720, 1020))
        self.assertEqual(DayParts.window("evening", wake=450, bed=1410), (1020, 1410))
        self.assertEqual(DayParts.window("before_bed", wake=450, bed=1410), (1290, 1410))
        # A night owl waking at 10:30: the morning is 10:30-12:00.
        self.assertEqual(DayParts.window("morning", wake=630, bed=1439), (630, 720))


class InItsPart(unittest.TestCase):
    def test_evening_takes_the_first_free_stretch_after_1700(self):
        s = plan({"habits/m.yml": habit("Meditate", 15, when="evening")})
        self.assertEqual(where(s, "Meditate"), ["17:00-17:15"])
        self.assertTrue(wish(s, "Meditate")["placed"])

    def test_morning_after_breakfast_when_planning_from_now(self):
        s = plan({"habits/m.yml": habit("Stretch", 15, when="morning")}, from_now=True)
        self.assertEqual(where(s, "Stretch"), ["08:30-08:45"])

    def test_before_bed_ends_at_bedtime(self):
        s = plan({"habits/r.yml": habit("Read in bed", 30, when="before bed")})
        self.assertEqual(where(s, "Read in bed"), ["23:00-23:30"])

    def test_two_before_bed_items_stack_back_from_bedtime(self):
        s = plan({"habits/a.yml": habit("Read in bed", 30, when="before bed"),
                  "habits/b.yml": habit("Teeth", 15, when="before bed")})
        spans = sorted(where(s, "Read in bed") + where(s, "Teeth"))
        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[-1][-5:], "23:30")              # the later one ends at bedtime
        self.assertEqual(spans[0][-5:], spans[1][:5])          # the other ends where it starts

    def test_a_routine_before_bed(self):
        routine = {"name": "Evening Wind-down", "type": "routine", "frequency": "daily", "when": "before bed",
                   "children": [{"type": "habit", "name": "Stretch", "duration": 10},
                                {"type": "habit", "name": "Journal", "duration": 15}]}
        s = plan({"routines/w.yml": routine,
                  "habits/s.yml": {"name": "Stretch", "type": "habit", "duration": 10},
                  "habits/j.yml": {"name": "Journal", "type": "habit", "duration": 15}})
        self.assertEqual(where(s, "Evening Wind-down"), ["23:05-23:30"])

    def test_when_as_a_clock_time(self):
        s = plan({"habits/m.yml": habit("Meditate", 15, when="21:00")})
        self.assertEqual(where(s, "Meditate"), ["21:00-21:15"])


class WhenThePartHasNoRoom(unittest.TestCase):
    def test_no_free_time_in_the_afternoon(self):
        s = plan({"habits/s.yml": habit("Stretch", 15, when="afternoon")})
        row = wish(s, "Stretch")
        self.assertFalse(row["placed"])
        self.assertIn("no free time in the afternoon", row["why"])
        self.assertEqual(len(where(s, "Stretch")), 1)          # planned anyway

    def test_the_morning_has_passed(self):
        s = plan({"habits/s.yml": habit("Stretch", 15, when="morning")}, now=datetime(2026, 4, 16, 20, 0), from_now=True)
        row = wish(s, "Stretch")
        self.assertFalse(row["placed"])
        self.assertIn("the morning has passed", row["why"])

    def test_a_part_after_bedtime_is_not_in_this_plan(self):
        # Added 2026-11-20 (found in the browser walk): at 00:30 a night owl's plan
        # (Core Sleep 02:00-10:30, the pilot's shape) ends at 02:00; their morning
        # (10:30-12:00) is after that, so it is not placed in this plan.
        night_owl = {"name": "My Day", "type": "day", "children": [
            {"name": "Core Sleep", "type": "timeblock", "start_time": "02:00", "end_time": "10:30",
             "reschedule": "never", "category": "sleep"}]}
        s = plan({"habits/s.yml": habit("Stretch", 15, when="morning")},
                 now=datetime(2026, 4, 16, 0, 30), template=night_owl, from_now=True)
        row = wish(s, "Stretch")
        self.assertFalse(row["placed"])
        self.assertIn("after bedtime (02:00)", row["why"])
        self.assertNotIn("10:30-10:45", where(s, "Stretch"))

    def test_a_when_chronos_does_not_know(self):
        s = plan({"habits/s.yml": habit("Stretch", 15, when="sometime")})
        row = wish(s, "Stretch")
        self.assertFalse(row["placed"])
        self.assertIn("not a part of the day", row["why"])
        self.assertEqual(len(where(s, "Stretch")), 1)

    def test_home_says_it(self):
        meta = {"wished_times": [{"name": "Stretch", "wished": "the afternoon", "placed": False,
                                  "why": "there was no free time in the afternoon"}]}
        self.assertEqual(home_api.plan_notes(meta), [
            "Stretch was meant for the afternoon, but there was no free time in the afternoon, so Chronos planned it in free time instead."])


if __name__ == "__main__":
    unittest.main()
