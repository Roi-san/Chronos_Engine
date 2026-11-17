"""
Status scale-down for fixed slots in the day template (step 2 of
docs/scheduling/status_scale_down_design.md, decision 7).

A slot like "Gym 18:00" keeps its time when today falls short: the lighter
version takes the slot, or, with no lighter version, the same keep/save rule as
flexible items applies. A saved slot frees its time for other work.

Fixture clock: Thursday 2026-04-16, 08:00.
"""
import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from test_kairos_v2_direction import SLEEP, _commitment
from test_kairos_v2_status_scale_down import EXHAUSTED, GOOD, LOW, MEDIUM, _plan, _saved, needs

SLOT = {"name": "Gym", "type": "habit", "start_time": "18:00", "duration": 60}


def _day(*children):
    return {"name": "Plain Day", "type": "day", "children": [SLEEP, *children]}


def gym_item(**extra):
    return {"habits/gym.yml": {"name": "Gym", "type": "habit", "duration": "60m", **extra}}


def mobility_item(**extra):
    return {"habits/mobility.yml": {"name": "Mobility", "type": "habit", "duration": "20m", "mini_of": "Gym", **extra}}


def _blocks(schedule):
    """Every placed block as (name, start, end), children included."""
    out = []

    def walk(blocks):
        for block in blocks or []:
            out.append((block.get("name"), block.get("start_time"), block.get("end_time")))
            walk(block.get("children"))

    walk(schedule.get("conceptual_schedule", {}).get("conceptual_blocks"))
    return out


def _starts(schedule, name):
    return [start for block_name, start, _ in _blocks(schedule) if block_name == name]


class FixedSlotKeepsItsTime(unittest.TestCase):
    def test_a_slot_that_fits_is_unchanged(self):
        schedule = _plan({**gym_item(**needs(energy="high")), **mobility_item()}, status=GOOD, day=_day(SLOT))
        self.assertEqual(_starts(schedule, "Gym"), ["18:00"])
        self.assertEqual(_starts(schedule, "Mobility"), [])

    def test_short_with_a_lighter_version_takes_the_same_slot(self):
        schedule = _plan({**gym_item(**needs(energy="high")), **mobility_item()}, status=MEDIUM, day=_day(SLOT))
        self.assertEqual(_starts(schedule, "Gym"), [])
        self.assertEqual(_starts(schedule, "Mobility"), ["18:00"])

    def test_the_lighter_version_uses_its_own_length(self):
        schedule = _plan({**gym_item(**needs(energy="high")), **mobility_item()}, status=MEDIUM, day=_day(SLOT))
        [(name, start, end)] = [row for row in _blocks(schedule) if row[0] == "Mobility"]
        self.assertEqual((start, end), ("18:00", "18:20"))

    def test_the_lighter_version_is_not_also_scheduled_elsewhere(self):
        schedule = _plan({**gym_item(frequency="daily", **needs(energy="high")),
                          **mobility_item(frequency="daily")}, status=EXHAUSTED, day=_day(SLOT))
        self.assertEqual(_starts(schedule, "Mobility"), ["18:00"])
        self.assertEqual(_starts(schedule, "Gym"), [])

    def test_requirements_written_on_the_slot_itself_count(self):
        schedule = _plan(mobility_item(), status=EXHAUSTED, day=_day({**SLOT, **needs(energy="high")}))
        self.assertEqual(_starts(schedule, "Mobility"), ["18:00"])

    def test_the_swap_is_recorded_with_its_slot(self):
        summary = _plan({**gym_item(**needs(energy="high")), **mobility_item()}, status=MEDIUM,
                        day=_day(SLOT))["status_scale_down"]
        [row] = [row for row in summary["swapped"] if row.get("fixed_slot")]
        self.assertEqual((row["from"], row["to"], row["fixed_slot"]), ("Gym", "Mobility", "18:00-19:00"))


class FixedSlotWithoutALighterVersion(unittest.TestCase):
    def test_one_step_short_stays_in_its_slot(self):
        schedule = _plan(gym_item(**needs(energy="high")), status=MEDIUM, day=_day(SLOT))
        self.assertEqual(_starts(schedule, "Gym"), ["18:00"])

    def test_far_short_frees_the_slot(self):
        schedule = _plan(gym_item(**needs(energy="high")), status=LOW, day=_day(SLOT))
        self.assertEqual(_starts(schedule, "Gym"), [])
        self.assertIn("Gym", _saved(schedule))
        saved = [row for row in schedule["status_scale_down"]["saved"] if row["name"] == "Gym"]
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["fixed_slot"], "18:00-19:00")

    def test_freed_time_becomes_a_gap_other_work_can_use(self):
        schedule = _plan(gym_item(**needs(energy="high")), status=LOW, day=_day(SLOT))
        gaps = schedule.get("gap_buffer_recovery", {}).get("emergent_gaps", [])
        self.assertTrue(any(
            gap.get("start_minutes", 10**9) <= 18 * 60 and gap.get("end_minutes", 0) >= 19 * 60 for gap in gaps
        ), gaps)

    def test_a_last_chance_commitment_keeps_the_slot(self):
        schedule = _plan({
            **gym_item(**needs(energy="high")),
            "commitments/c.yml": _commitment(times=4, targets=[{"type": "habit", "name": "Gym"}]),
        }, status=LOW, day=_day(SLOT))
        self.assertEqual(_starts(schedule, "Gym"), ["18:00"])

    def test_a_near_goal_keeps_the_slot(self):
        schedule = _plan({
            **gym_item(goal="Ship it", **needs(energy="high")),
            "goals/ship.yml": {"name": "Ship it", "type": "goal", "priority": "high", "due_date": "2026-04-18"},
        }, status=LOW, day=_day(SLOT))
        self.assertEqual(_starts(schedule, "Gym"), ["18:00"])


class FixedSlotSafeDefaults(unittest.TestCase):
    def test_no_status_set_changes_nothing(self):
        schedule = _plan({**gym_item(**needs(energy="high")), **mobility_item()}, status={}, day=_day(SLOT))
        self.assertEqual(_starts(schedule, "Gym"), ["18:00"])

    def test_a_slot_without_requirements_is_untouched(self):
        schedule = _plan({**gym_item(), **mobility_item()}, status=EXHAUSTED, day=_day(SLOT))
        self.assertEqual(_starts(schedule, "Gym"), ["18:00"])
        self.assertEqual(_starts(schedule, "Mobility"), [])

    def test_anchors_are_never_touched(self):
        anchor = {**SLOT, "name": "Dentist", "type": "appointment", "reschedule": "never", **needs(energy="high")}
        self.assertEqual(_starts(_plan({}, status=EXHAUSTED, day=_day(anchor)), "Dentist"), ["18:00"])


if __name__ == "__main__":
    unittest.main()
