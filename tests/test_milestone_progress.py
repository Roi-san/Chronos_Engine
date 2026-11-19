"""
Milestone progress (issue 41 c and d, 2026-11-19).

(c) Goal Planning saves a milestone's success measure as text in `criteria`
    ("run 10 times, count them"). `_compute_progress` checked `'count' in criteria`,
    which on a string is a substring test, then indexed the string: TypeError. The
    loop over all milestones stopped there, and the caller swallowed the error, so
    no milestone updated again, silently. Now a text measure is simply "not
    countable", and one milestone that fails cannot stop the others.
(d) Completing a milestone by hand (the Milestones widget's button runs
    `set milestone "<name>" status:completed`) kept `progress.percent: 0`, and every
    goal percentage is computed from the milestones' stored percent, so a goal with
    2 of 4 milestones completed showed 25%. Now completed means 100%, and going back
    to pending makes a hand-completed (not countable) milestone 0% again.
"""
import io
import os
import sys
import unittest
from contextlib import redirect_stdout

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.dirname(__file__)
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from chronos_fixture import temporary_kairos_user_fixture  # noqa: E402
from modules.item_manager import read_item_data, write_item_data  # noqa: E402
from modules.milestone import main as Milestones  # noqa: E402
from modules.goal import main as Goals  # noqa: E402
from commands import set as SetCommand  # noqa: E402


def quiet(fn, *args, **kwargs):
    out = io.StringIO()
    with redirect_stdout(out):
        result = fn(*args, **kwargs)
    return result, out.getvalue()


class MilestoneProgressTests(unittest.TestCase):
    def setUp(self):
        self._fixture = temporary_kairos_user_fixture()
        self._fixture.__enter__()
        write_item_data("goal", "Get fit", {"name": "Get fit", "type": "goal", "status": "active"})
        write_item_data("task", "Plan my workouts", {"name": "Plan my workouts", "type": "task", "status": "completed"})
        self.checklist = {
            "name": "Workout plan ready", "type": "milestone", "goal": "Get fit", "status": "pending",
            "progress": {"percent": 0},
            "criteria": {"checklist": {"items": [{"type": "task", "name": "Plan my workouts"}], "require": "all"}},
        }

    def tearDown(self):
        self._fixture.__exit__(None, None, None)

    def milestone(self, name, criteria, status="pending"):
        write_item_data("milestone", name, {
            "name": name, "type": "milestone", "goal": "Get fit", "status": status,
            "progress": {"percent": 0}, "criteria": criteria,
        })

    def test_text_measure_with_the_word_count_does_not_crash(self):
        self.milestone("Lower count", "run 10 times, count them")
        write_item_data("milestone", "Workout plan ready", self.checklist)
        quiet(Milestones.evaluate_and_update_milestones)
        self.assertEqual(read_item_data("milestone", "Workout plan ready")["status"], "completed")
        self.assertEqual(read_item_data("milestone", "Lower count")["status"], "pending")

    def test_one_broken_milestone_does_not_stop_the_others(self):
        # A countable shape with a nonsense number: int("lots") raises.
        self.milestone("Broken", {"count": {"of": {"type": "task", "name": "Plan my workouts"}, "times": "lots"}})
        write_item_data("milestone", "Workout plan ready", self.checklist)
        _, out = quiet(Milestones.evaluate_and_update_milestones)
        self.assertEqual(read_item_data("milestone", "Workout plan ready")["status"], "completed")
        self.assertIn("Broken", out)

    def test_completed_by_hand_is_100_percent_and_counts_for_the_goal(self):
        self.milestone("First 5k", "Run 5k without stopping")
        self.milestone("First 10k", "Run 10k")
        quiet(SetCommand.run, ["milestone", "First 5k"], {"status": "completed"})
        self.assertEqual(read_item_data("milestone", "First 5k")["progress"]["percent"], 100)
        _, out = quiet(Goals._track_goal, "Get fit")
        self.assertIn("Overall: 50%", out)

    def test_back_to_pending_after_a_hand_completion_is_0_percent(self):
        self.milestone("First 5k", "Run 5k without stopping")
        quiet(SetCommand.run, ["milestone", "First 5k"], {"status": "completed"})
        quiet(SetCommand.run, ["milestone", "First 5k"], {"status": "pending"})
        self.assertEqual(read_item_data("milestone", "First 5k")["progress"]["percent"], 0)

    def test_countable_milestone_keeps_its_computed_progress(self):
        # Unchanged behaviour: a count milestone at 1 of 2 stays at 50%.
        write_item_data("habit", "Run", {"name": "Run", "type": "habit", "completion_dates": ["2026-11-19"]})
        self.milestone("Two runs", {"count": {"of": {"type": "habit", "name": "Run"}, "times": 2, "period": "all"}})
        quiet(Milestones.evaluate_and_update_milestones)
        m = read_item_data("milestone", "Two runs")
        self.assertEqual(m["progress"]["percent"], 50.0)
        self.assertEqual(m["status"], "in-progress")


if __name__ == "__main__":
    unittest.main()
