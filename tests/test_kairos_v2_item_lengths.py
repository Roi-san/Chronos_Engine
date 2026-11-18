"""Items without a length still get planned (decision D1, issue 12, 2026-11-18).

Kairos drops anything without a positive length. Tasks made with `new` or the
Brain Dump wizard get `duration: 0`, and a routine without a length of its own
disappeared from the plan together with its steps. The rules
(docs/scheduling/item_lengths.md):

1. An item's own length always wins.
2. A routine (or subroutine, microroutine) without one is planned for the total
   of its steps' lengths.
3. A task or habit without one, or a routine whose steps have none, gets the
   default length: `default_duration_minutes` in scheduling_settings.yml, 30
   when not set.
4. What was assumed is recorded in `schedule.assumed_lengths`.
"""

import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from test_kairos_v2_gaps_and_breathing_room import _result, anchor, at, mins

TODAY = "2026-04-16"  # the fixture's Thursday
NOW = at(8, 0)
LUNCH = anchor("Lunch", "12:00", "12:30")


def _plan(children=None, files=None, now=NOW):
    return _result([LUNCH, *(children or [])], files or {}, now).get("schedule", {})


def _spans(schedule):
    """name -> (start, end) for every planned block, and for every item inside one."""
    out = {}
    for block in schedule.get("conceptual_schedule", {}).get("conceptual_blocks", []):
        children = block.get("children") or []
        for child in children:
            out.setdefault(child["name"], (child["start_time"], child["end_time"]))
        if not children:
            out.setdefault(block["name"], (block.get("start_time"), block.get("end_time")))
    return out


def _length(schedule, name):
    span = _spans(schedule).get(name)
    return None if span is None else mins(span[1]) - mins(span[0])


def _task(name, **extra):
    return {"name": name, "type": "task", "due_date": TODAY, **extra}


def _step(name, minutes=None, kind="habit"):
    node = {"name": name, "type": kind}
    if minutes is not None:
        node["duration"] = minutes
    return node


def _routine(name, steps, **extra):
    return {"name": name, "type": "routine", "children": steps, **extra}


MORNING_STEPS = [_step("Brush teeth", 5), _step("Shower", 15), _step("Make breakfast", 10, "task")]


class TasksAndHabitsWithoutALength(unittest.TestCase):
    def test_a_task_without_a_length_gets_the_default(self):
        self.assertEqual(_length(_plan(files={"tasks/bank.yml": _task("Call the bank")}), "Call the bank"), 30)

    def test_a_length_of_zero_counts_as_no_length(self):
        files = {"tasks/bank.yml": _task("Call the bank", duration=0)}
        self.assertEqual(_length(_plan(files=files), "Call the bank"), 30)

    def test_the_default_is_a_setting(self):
        files = {
            "tasks/bank.yml": _task("Call the bank"),
            "settings/scheduling_settings.yml": {"default_duration_minutes": 45},
        }
        self.assertEqual(_length(_plan(files=files), "Call the bank"), 45)

    def test_a_habit_without_a_length_gets_the_default(self):
        files = {"habits/stretch.yml": {"name": "Stretch", "type": "habit", "frequency": "daily"}}
        self.assertEqual(_length(_plan(files=files), "Stretch"), 30)

    def test_an_item_with_its_own_length_keeps_it(self):
        files = {"tasks/bank.yml": _task("Call the bank", duration="20m")}
        self.assertEqual(_length(_plan(files=files), "Call the bank"), 20)

    def test_a_timed_item_without_a_length_keeps_its_time(self):
        schedule = _plan([{"name": "Gym", "type": "habit", "start_time": "18:00"}])
        self.assertEqual(_spans(schedule).get("Gym"), ("18:00", "18:30"))


class RoutinesWithoutALength(unittest.TestCase):
    def test_a_routine_is_planned_for_the_total_of_its_steps(self):
        schedule = _plan([_routine("Morning Routine", MORNING_STEPS)])
        self.assertEqual(_length(schedule, "Morning Routine"), 30)

    def test_its_steps_are_not_planned_a_second_time(self):
        spans = _spans(_plan([_routine("Morning Routine", MORNING_STEPS)]))
        for step in ("Brush teeth", "Shower", "Make breakfast"):
            self.assertNotIn(step, spans)

    def test_a_routine_with_its_own_length_keeps_it(self):
        schedule = _plan([_routine("Morning Routine", MORNING_STEPS, duration=20)])
        self.assertEqual(_length(schedule, "Morning Routine"), 20)

    def test_a_routine_whose_steps_have_no_length_gets_the_default(self):
        steps = [_step("Brush teeth"), _step("Shower"), _step("Make breakfast", kind="task")]
        self.assertEqual(_length(_plan([_routine("Morning Routine", steps)]), "Morning Routine"), 30)

    def test_only_known_step_lengths_count(self):
        steps = [_step("Brush teeth", 10), _step("Shower"), _step("Make breakfast", 15, "task")]
        self.assertEqual(_length(_plan([_routine("Morning Routine", steps)]), "Morning Routine"), 25)

    def test_nested_routines_add_up(self):
        dental = {"name": "Dental", "type": "microroutine", "children": [_step("Brush teeth", 5), _step("Floss", 3)]}
        routine = _routine("Morning Routine", [dental, _step("Shower", 15)])
        self.assertEqual(_length(_plan([routine]), "Morning Routine"), 23)

    def test_a_library_routine_gets_its_steps_lengths_from_their_own_files(self):
        files = {
            "routines/morning.yml": _routine(
                "Morning Routine", [{"name": "Brush teeth", "type": "habit"}, {"name": "Shower", "type": "habit"}],
                frequency="daily",
            ),
            "habits/brush.yml": {"name": "Brush teeth", "type": "habit", "duration": 5},
            "habits/shower.yml": {"name": "Shower", "type": "habit", "duration": 15},
        }
        self.assertEqual(_length(_plan(files=files), "Morning Routine"), 20)

    def test_a_timed_routine_without_a_length_keeps_its_time(self):
        routine = _routine("Evening Routine", [_step("Tidy up", 10), _step("Read", 20)], start_time="21:00")
        self.assertEqual(_spans(_plan([routine])).get("Evening Routine"), ("21:00", "21:30"))


class TheRecord(unittest.TestCase):
    def test_assumed_lengths_are_recorded(self):
        schedule = _plan([_routine("Morning Routine", MORNING_STEPS)], {"tasks/bank.yml": _task("Call the bank")})
        rows = {row["name"]: row for row in schedule.get("assumed_lengths") or []}
        self.assertEqual((rows["Call the bank"]["minutes"], rows["Call the bank"]["source"]), (30, "default"))
        self.assertEqual((rows["Morning Routine"]["minutes"], rows["Morning Routine"]["source"]), (30, "steps"))
        self.assertEqual(rows["Call the bank"]["type"], "task")

    def test_items_with_their_own_length_are_not_listed(self):
        schedule = _plan(files={"tasks/bank.yml": _task("Call the bank", duration=20)})
        self.assertEqual(schedule.get("assumed_lengths"), [])


if __name__ == "__main__":
    unittest.main()
