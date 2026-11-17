"""
A finished one-off task must not come back on later days.

`mark "<task>":completed` writes `status: completed` onto a task that has no
`frequency`; `complete task <name>` now does the same. Kairos v2 skips such a
task when it builds the candidate universe, unless an unmet commitment still
needs it (commitment targets are meant to repeat). Recurring items are never
affected by their `status`.
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
from commands import complete as Complete
from modules.item_manager import read_item_data, write_item_data
from test_kairos_v2_direction import _candidate, _commitment, _placed, _run

# Fixture clock is Thursday 2026-04-16; the rent was due the day before.
RENT = {"name": "Pay rent", "type": "task", "duration": "30m", "priority": "high", "due_date": "2026-04-15"}


def _universe(schedule):
    return [row.get("name") for row in schedule.get("candidate_universe", {}).get("candidates", [])]


class FinishedOneOffTasks(unittest.TestCase):
    def test_an_open_overdue_task_is_still_scheduled(self):
        schedule = _run({"tasks/rent.yml": {**RENT, "status": "pending"}})
        self.assertIn("Pay rent", _placed(schedule))

    def test_a_completed_one_off_task_does_not_come_back(self):
        schedule = _run({"tasks/rent.yml": {**RENT, "status": "completed", "completion_dates": ["2026-04-15"]}})
        self.assertNotIn("Pay rent", _universe(schedule))
        self.assertNotIn("Pay rent", _placed(schedule))

    def test_status_is_read_case_insensitively(self):
        schedule = _run({"tasks/rent.yml": {**RENT, "Status": "Completed"}})
        self.assertNotIn("Pay rent", _universe(schedule))

    def test_skipped_is_not_finished(self):
        schedule = _run({"tasks/rent.yml": {**RENT, "status": "skipped"}})
        self.assertIn("Pay rent", _placed(schedule))

    def test_reopening_a_task_brings_it_back(self):
        schedule = _run({"tasks/rent.yml": {**RENT, "status": "pending", "completion_dates": ["2026-04-15"]}})
        self.assertIn("Pay rent", _placed(schedule))

    def test_a_completed_task_that_served_a_goal_does_not_come_back(self):
        schedule = _run({
            "tasks/post.yml": {"name": "Write launch post", "type": "task", "duration": "45m",
                               "goal": "Ship it", "status": "completed"},
            "goals/ship.yml": {"name": "Ship it", "type": "goal", "priority": "high", "due_date": "2026-04-18"},
        })
        self.assertNotIn("Write launch post", _universe(schedule))

    def test_status_does_not_hide_a_recurring_item(self):
        schedule = _run({"habits/stretch.yml": {"name": "Stretch", "type": "habit", "duration": "10m",
                                                "frequency": "daily", "status": "completed"}})
        self.assertIn("Stretch", _placed(schedule))

    def test_a_completed_task_an_unmet_commitment_needs_stays_in_scope(self):
        schedule = _run({
            "tasks/run.yml": {"name": "Morning run", "type": "task", "duration": "30m", "status": "completed"},
            "commitments/c.yml": _commitment(targets=[{"type": "task", "name": "Morning run"}]),
        })
        self.assertIn("Morning run", _universe(schedule))
        self.assertIn("commitment_needs_progress", _candidate(schedule, "Morning run")["reasons"])


class CompleteClosesOneOffTasks(unittest.TestCase):
    def test_complete_marks_a_one_off_task_completed(self):
        with temporary_kairos_user_fixture():
            write_item_data("task", "Pay rent", {**RENT, "status": "pending"})
            Complete.close_one_off_item("task", "Pay rent")
            self.assertEqual(read_item_data("task", "Pay rent").get("status"), "completed")

    def test_complete_leaves_a_recurring_task_open(self):
        with temporary_kairos_user_fixture():
            write_item_data("task", "Water plants", {"name": "Water plants", "type": "task",
                                                     "duration": 5, "frequency": "monday", "status": "pending"})
            Complete.close_one_off_item("task", "Water plants")
            self.assertEqual(read_item_data("task", "Water plants").get("status"), "pending")

    def test_complete_only_closes_tasks(self):
        with temporary_kairos_user_fixture():
            write_item_data("routine", "Spring clean", {"name": "Spring clean", "type": "routine",
                                                        "duration": 60, "status": "pending"})
            Complete.close_one_off_item("routine", "Spring clean")
            self.assertEqual(read_item_data("routine", "Spring clean").get("status"), "pending")


if __name__ == "__main__":
    unittest.main()
