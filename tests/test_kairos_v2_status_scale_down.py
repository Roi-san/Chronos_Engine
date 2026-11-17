"""
Status-aware scale-down for flexible items (design: docs/scheduling/status_scale_down_design.md).

Every test names the design decision it pins down. The status setup mirrors the
shipped `status_settings.yml`: seven dimensions, Health ranked first and Energy
third, so dimension weights are Health 1.0, Energy 5/7 = 0.71.

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

from chronos_fixture import temporary_kairos_user_fixture
from modules.scheduler.kairos_v2 import KairosV2Scheduler
from test_kairos_v2_direction import NOW, PLAIN_DAY, SLEEP, _candidate, _commitment, _placed, _seed, _write


def _status_settings(grace=None):
    rows = [{"Name": name, "Rank": rank} for rank, name in enumerate(
        ["Health", "Place", "Energy", "Mind State", "Focus", "Emotion", "Vibe"], start=1)]
    for row in rows:
        if grace and row["Name"] in grace:
            row["Grace"] = grace[row["Name"]]
    return {"settings/status_settings.yml": {"Status_Settings": rows}}


SCALES = {
    "settings/health_settings.yml": {"Health_Settings": {
        "Excellent": {"value": 1}, "Good": {"value": 2}, "Fair": {"value": 3}, "Poor": {"value": 4}, "Critical": {"value": 5}}},
    "settings/energy_settings.yml": {"Energy_Settings": {
        "High": {"value": 1}, "Medium": {"value": 2}, "Low": {"value": 3}, "Exhausted": {"value": 4}}},
    "settings/place_settings.yml": {"Place_Settings": {"At Home": {"value": 1}, "At Work": {"value": 3}}},
}
PRIORITIES = {"settings/scheduling_priorities.yml": {"Scheduling_Priorities": [
    {"Name": "Priority Property", "Order": 1, "Rank": 5},
    {"Name": "Goal Alignment", "Order": 2, "Rank": 5},
    {"Name": "Commitment Pressure", "Order": 3, "Rank": 5},
]}}


def _plan(files, *, status=None, grace=None, day=None, context=None, priorities=None):
    with temporary_kairos_user_fixture() as fixture:
        user_dir = fixture["user_dir"]
        days_dir = os.path.join(user_dir, "days")
        for name in os.listdir(days_dir):
            os.remove(os.path.join(days_dir, name))
        _write(os.path.join(days_dir, "plain_day.yml"), day or PLAIN_DAY)
        _seed(user_dir, {**_status_settings(grace), **SCALES, **(priorities or PRIORITIES), **files})
        if status is not None:
            _write(os.path.join(user_dir, "profile", "current_status.yml"), status)
        result = KairosV2Scheduler({"now": NOW, **(context or {})}).generate_schedule(NOW.date())
    return result.get("schedule", {})


def _saved(schedule):
    return {
        row["name"]: row
        for row in schedule.get("reality_filtered_candidates", {}).get("impossible_candidates", [])
        if row.get("impossible_reason") == "saved_for_better_day"
    }


def gym(**extra):
    return {"habits/gym.yml": {"name": "Gym", "type": "habit", "duration": "60m", "frequency": "daily", **extra}}


def mobility(**extra):
    return {"habits/mobility.yml": {"name": "Mobility", "type": "habit", "duration": "20m", "mini_of": "Gym", **extra}}


def needs(**requirements):
    return {"status_requirements": requirements}


GOOD = {"health": "good", "energy": "high"}
MEDIUM = {"health": "good", "energy": "medium"}
LOW = {"health": "good", "energy": "low"}
EXHAUSTED = {"health": "good", "energy": "exhausted"}
SICK = {"health": "poor", "energy": "low"}


class FitIsOneWay(unittest.TestCase):
    """Decision 1: better than needed is never a mismatch."""

    def test_a_better_day_than_needed_keeps_the_full_version(self):
        schedule = _plan({**gym(**needs(energy="medium")), **mobility()}, status=GOOD)
        self.assertIn("Gym", _placed(schedule))
        self.assertNotIn("Mobility", _placed(schedule))

    def test_a_low_energy_item_fits_a_high_energy_day(self):
        schedule = _plan({**gym(**needs(energy="low")), **mobility()}, status=GOOD)
        self.assertIn("Gym", _placed(schedule))
        self.assertNotIn("Mobility", _placed(schedule))

    def test_better_than_needed_has_no_distance(self):
        fit = _candidate(_plan(gym(**needs(energy="low")), status=GOOD), "Gym")["local_status_fit"]
        self.assertEqual(fit["weighted_distance"], 0)
        self.assertEqual(fit["max_short"], 0)

    def test_worse_than_needed_has_a_distance(self):
        fit = _candidate(_plan(gym(**needs(energy="high")), status=MEDIUM), "Gym")["local_status_fit"]
        self.assertGreater(fit["weighted_distance"], 0)
        self.assertEqual(fit["max_short"], 1)

    def test_any_accepted_value_counts(self):
        schedule = _plan({**gym(**needs(energy=["high", "medium"])), **mobility()}, status=MEDIUM)
        self.assertIn("Gym", _placed(schedule))
        self.assertNotIn("Mobility", _placed(schedule))


class GraceAndLighterVersions(unittest.TestCase):
    """Decisions 2, 3, 4."""

    def test_one_step_short_without_a_lighter_version_stays(self):
        schedule = _plan(gym(**needs(energy="high")), status=MEDIUM)
        self.assertIn("Gym", _placed(schedule))
        self.assertEqual(_candidate(schedule, "Gym")["status_note"]["kind"], "within_grace")

    def test_one_step_short_with_a_lighter_version_swaps(self):
        schedule = _plan({**gym(**needs(energy="high")), **mobility()}, status=MEDIUM)
        self.assertIn("Mobility", _placed(schedule))
        self.assertNotIn("Gym", _placed(schedule))

    def test_far_short_with_a_lighter_version_swaps_instead_of_saving(self):
        schedule = _plan({**gym(**needs(energy="high")), **mobility()}, status=EXHAUSTED)
        self.assertIn("Mobility", _placed(schedule))
        self.assertNotIn("Gym", _saved(schedule))

    def test_when_neither_fits_the_lighter_version_stays_visible(self):
        schedule = _plan({**gym(**needs(energy="high")), **mobility(**needs(energy="medium"))}, status=EXHAUSTED)
        self.assertIn("Mobility", _placed(schedule))
        self.assertNotIn("Gym", _placed(schedule))

    def test_a_lighter_version_that_demands_more_is_not_used(self):
        schedule = _plan({**gym(**needs(energy="medium")), **mobility(**needs(energy="high"))}, status=LOW)
        self.assertIn("Gym", _placed(schedule))
        self.assertNotIn("Mobility", _placed(schedule))

    def test_the_swap_keeps_its_record(self):
        swaps = _plan({**gym(**needs(energy="high")), **mobility()}, status=MEDIUM)["reality_filtered_candidates"]["scaled_down"]
        self.assertEqual([(row["from"], row["to"]) for row in swaps], [("Gym", "Mobility")])


class SavedForABetterDay(unittest.TestCase):
    """Decision 8: far short, no lighter version, not urgent, not important enough."""

    def test_far_short_is_saved_for_a_better_day(self):
        schedule = _plan(gym(**needs(energy="high")), status=LOW)
        self.assertNotIn("Gym", _placed(schedule))
        self.assertIn("Gym", _saved(schedule))

    def test_the_saved_record_explains_why(self):
        row = _saved(_plan(gym(**needs(energy="high")), status=EXHAUSTED))["Gym"]
        verdict = row["status_verdict"]
        self.assertEqual(verdict["kind"], "saved")
        self.assertAlmostEqual(verdict["strain"], round(2 * 5 / 7, 3))
        self.assertEqual(verdict["importance"], 0.0)
        [dim] = verdict["short_dimensions"]
        self.assertEqual((dim["dimension"], dim["today"], dim["steps_short"], dim["beyond_grace"]),
                         ("energy", "exhausted", 3, 2))

    def test_sick_day_adds_up_across_dimensions(self):
        row = _saved(_plan(gym(**needs(health="good", energy="high")), status=SICK))["Gym"]
        self.assertAlmostEqual(row["status_verdict"]["strain"], round(1.0 + 5 / 7, 3))

    def test_the_decision_log_summarises_it(self):
        summary = _plan(gym(**needs(energy="high")), status=LOW)["status_scale_down"]
        self.assertEqual([row["name"] for row in summary["saved"]], ["Gym"])


class Urgent(unittest.TestCase):
    """Decision 5: due/deadline today or overdue, or a commitment at last chance / behind."""

    def _task(self, **extra):
        return {"tasks/t.yml": {"name": "Gym", "type": "task", "duration": "60m", **needs(energy="high"), **extra}}

    def test_due_today_stays(self):
        schedule = _plan(self._task(due_date="2026-04-16"), status=EXHAUSTED)
        self.assertIn("Gym", _placed(schedule))
        self.assertEqual(_candidate(schedule, "Gym")["status_note"]["kind"], "urgent")

    def test_overdue_deadline_stays(self):
        schedule = _plan(self._task(deadline="2026-04-14"), status=EXHAUSTED)
        self.assertIn("Gym", _placed(schedule))

    def test_due_tomorrow_is_not_urgent(self):
        schedule = _plan(self._task(due_date="2026-04-17"), status=EXHAUSTED)
        self.assertIn("Gym", _saved(schedule))

    def test_last_chance_commitment_stays_on_a_sick_day(self):
        schedule = _plan({
            **gym(frequency="monday", **needs(health="good", energy="high")),
            "commitments/c.yml": _commitment(times=4, targets=[{"type": "habit", "name": "Gym"}]),
        }, status=SICK)
        self.assertIn("Gym", _placed(schedule))
        self.assertEqual(_candidate(schedule, "Gym")["status_note"]["kind"], "urgent")


class ImportanceOutweighsStrain(unittest.TestCase):
    """Decision 8 + open questions 1-2: goals, commitments and priority, x the 0-10 weights; close calls keep."""

    GOAL = {"goals/ship.yml": {"name": "Ship it", "type": "goal", "priority": "high", "due_date": "2026-04-18"}}

    def test_a_near_goal_outweighs_low_energy(self):
        schedule = _plan({**gym(goal="Ship it", **needs(energy="high")), **self.GOAL}, status=LOW)
        self.assertIn("Gym", _placed(schedule))
        note = _candidate(schedule, "Gym")["status_note"]
        self.assertEqual(note["kind"], "important")
        self.assertAlmostEqual(note["importance"], 0.9)

    def test_the_same_goal_does_not_outweigh_exhaustion(self):
        schedule = _plan({**gym(goal="Ship it", **needs(energy="high")), **self.GOAL}, status=EXHAUSTED)
        self.assertIn("Gym", _saved(schedule))

    def test_a_close_call_keeps_the_item(self):
        # At-risk commitment 0.70 vs low-energy strain 0.71: within the 0.1 margin.
        schedule = _plan({
            **gym(frequency="monday", **needs(energy="high")),
            "commitments/c.yml": _commitment(targets=[{"type": "habit", "name": "Gym"}]),
        }, status=LOW)
        self.assertIn("Gym", _placed(schedule))
        self.assertEqual(_candidate(schedule, "Gym")["status_note"]["kind"], "important")

    def test_a_zero_weight_switches_importance_off(self):
        priorities = {"settings/scheduling_priorities.yml": {"Scheduling_Priorities": [
            {"Name": "Commitment Pressure", "Order": 1, "Rank": 0}]}}
        schedule = _plan({
            **gym(frequency="monday", **needs(energy="high")),
            "commitments/c.yml": _commitment(targets=[{"type": "habit", "name": "Gym"}]),
        }, status=LOW, priorities=priorities)
        self.assertIn("Gym", _saved(schedule))

    def test_critical_priority_outweighs_low_energy(self):
        schedule = _plan(gym(priority="critical", **needs(energy="high")), status=LOW)
        self.assertIn("Gym", _placed(schedule))

    def test_high_priority_is_a_close_call_on_low_energy(self):
        # 0.7 vs 0.71: kept.
        schedule = _plan(gym(priority="high", **needs(energy="high")), status=LOW)
        self.assertIn("Gym", _placed(schedule))

    def test_medium_priority_does_not_outweigh_low_energy(self):
        schedule = _plan(gym(priority="medium", **needs(energy="high")), status=LOW)
        self.assertIn("Gym", _saved(schedule))


class UserControls(unittest.TestCase):
    """Decision 9: grace per dimension (status_settings.yml) and per item (status_grace)."""

    def test_dimension_grace_zero_is_strict(self):
        schedule = _plan(gym(**needs(energy="high")), status=MEDIUM, grace={"Energy": 0})
        self.assertIn("Gym", _saved(schedule))

    def test_dimension_grace_two_is_loose(self):
        schedule = _plan(gym(**needs(energy="high")), status=LOW, grace={"Energy": 2})
        self.assertIn("Gym", _placed(schedule))

    def test_item_grace_overrides_the_dimension(self):
        strict = _plan(gym(status_grace=0, **needs(energy="high")), status=MEDIUM)
        self.assertIn("Gym", _saved(strict))
        loose = _plan(gym(status_grace=3, **needs(energy="high")), status=EXHAUSTED)
        self.assertIn("Gym", _placed(loose))

    def test_added_back_by_hand_is_never_removed(self):
        schedule = _plan(gym(frequency="monday", **needs(energy="high")), status=EXHAUSTED,
                         context={"manual_injections": [{"name": "Gym", "type": "habit", "mode": "soft"}]})
        self.assertIn("Gym", _placed(schedule))


class SafeDefaults(unittest.TestCase):
    """What must never change: no status, unknown values, undeclared dimensions, place, anchors."""

    def test_no_status_set_changes_nothing(self):
        self.assertIn("Gym", _placed(_plan(gym(**needs(energy="high")), status={})))

    def test_an_unknown_value_is_ignored(self):
        self.assertIn("Gym", _placed(_plan(gym(**needs(energy="hgih")), status=EXHAUSTED)))

    def test_an_undeclared_dimension_is_ignored(self):
        self.assertIn("Gym", _placed(_plan(gym(**needs(stamina="high")), status=EXHAUSTED)))

    def test_place_is_ignored(self):
        self.assertIn("Gym", _placed(_plan(gym(**needs(place="at_work")), status={**EXHAUSTED, "place": "at_home"})))

    def test_capitalised_requirement_keys_count(self):
        self.assertIn("Gym", _saved(_plan(gym(**needs(Energy="High")), status=LOW)))

    def test_items_without_requirements_are_untouched(self):
        self.assertIn("Gym", _placed(_plan(gym(), status=SICK)))

    def test_anchors_are_never_touched(self):
        day = {"name": "Plain Day", "type": "day", "children": [SLEEP, {
            "name": "Dentist", "type": "appointment", "start_time": "10:00", "duration": 60,
            "reschedule": "never", **needs(energy="high")}]}
        self.assertIn("Dentist", _placed(_plan({}, status=EXHAUSTED, day=day)))


if __name__ == "__main__":
    unittest.main()
