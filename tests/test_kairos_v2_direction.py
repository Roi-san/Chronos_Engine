"""
Goals and commitments as scheduling pressure (modules/scheduler/direction.py),
and scaling an item down to its authored mini when today's status does not fit.
"""
import os
import sys
import tempfile
import unittest
from datetime import date, datetime

import yaml

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from chronos_fixture import temporary_kairos_user_fixture
from modules.scheduler import direction as Direction
from modules.scheduler.kairos_v2 import KairosV2Scheduler

# The fixture clock: Thursday 16 April 2026, 08:00. Week = Mon 13 .. Sun 19.
NOW = datetime(2026, 4, 16, 8, 0, 0)
THURSDAY = NOW.date()
FRIDAY = date(2026, 4, 17)
SUNDAY = date(2026, 4, 19)

SLEEP = {"type": "timeblock", "name": "Sleep", "duration": 480, "start_time": "23:30",
         "end_time": "07:30", "reschedule": "never"}
PLAIN_DAY = {"name": "Plain Day", "type": "day", "children": [SLEEP]}


def _write(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def _seed(user_dir, files):
    for rel_path, payload in files.items():
        _write(os.path.join(user_dir, rel_path), payload)


def _gym(**extra):
    return {"name": "Gym session", "type": "habit", "duration": "60m", **extra}


def _commitment(times=3, period="week", targets=None):
    return {
        "name": "Three workouts a week",
        "type": "commitment",
        "status": "active",
        # Capitalised nested keys, as commitment_defaults.yml writes them.
        "Rule": {"Kind": "frequency", "Times": times, "Period": period},
        "targets": targets or [{"type": "habit", "name": "Gym session"}],
    }


class DirectionSignals(unittest.TestCase):
    """Pure signal maths, no scheduler involved."""

    def _load(self, files, day=THURSDAY):
        with tempfile.TemporaryDirectory() as user_dir:
            _seed(user_dir, files)
            return Direction.load_direction(user_dir, day)

    def _commitment_signal(self, files, day=THURSDAY):
        return self._load(files, day)["by_identity"].get("habit:gym session", {}).get("commitment")

    def test_pressure_rises_as_the_week_runs_out(self):
        files = {"habits/gym.yml": _gym(), "commitments/c.yml": _commitment()}
        thursday = self._commitment_signal(files, THURSDAY)   # 3 to do, 4 days left
        friday = self._commitment_signal(files, FRIDAY)       # 3 to do, 3 days left
        self.assertEqual((thursday["state"], thursday["level"]), ("at_risk", 0.7))
        self.assertEqual((friday["state"], friday["level"]), ("last_chance", 1.0))

    def test_too_late_to_fully_catch_up_still_pushes_at_maximum(self):
        files = {"habits/gym.yml": _gym(), "commitments/c.yml": _commitment()}
        sunday = self._commitment_signal(files, SUNDAY)       # 3 to do, 1 day left
        self.assertEqual((sunday["state"], sunday["level"]), ("behind", 1.0))

    def test_progress_relieves_pressure_and_a_met_commitment_pushes_nothing(self):
        two_done = {"habits/gym.yml": _gym(completion_dates=["2026-04-13", "2026-04-14"]),
                    "commitments/c.yml": _commitment()}
        signal = self._commitment_signal(two_done)            # 1 to do, 4 days left
        self.assertEqual((signal["state"], signal["level"]), ("on_track", 0.2))

        met = {"habits/gym.yml": _gym(completion_dates=["2026-04-13", "2026-04-14", "2026-04-15"]),
               "commitments/c.yml": _commitment()}
        loaded = self._load(met)
        self.assertNotIn("habit:gym session", loaded["by_identity"])
        self.assertEqual(loaded["commitments"][0]["state"], "met")

    def test_a_missed_previous_week_adds_pressure(self):
        # Did it two weeks ago, nothing last week, one so far this week.
        files = {"habits/gym.yml": _gym(completion_dates=["2026-03-31", "2026-04-01", "2026-04-02", "2026-04-13", "2026-04-14"]),
                 "commitments/c.yml": _commitment()}
        signal = self._commitment_signal(files)
        self.assertEqual(signal["state"], "on_track")
        self.assertAlmostEqual(signal["level"], 0.4)          # 0.2 + 0.2 carried over
        self.assertIn("missed last time", signal["reason"])

    def test_a_brand_new_commitment_is_not_treated_as_missed(self):
        files = {"habits/gym.yml": _gym(completion_dates=["2026-04-13", "2026-04-14"]),
                 "commitments/c.yml": _commitment()}
        self.assertEqual(self._commitment_signal(files)["level"], 0.2)

    def test_completing_the_mini_counts_toward_the_commitment(self):
        files = {
            "habits/gym.yml": _gym(completion_dates=["2026-04-13"]),
            "habits/mobility.yml": {"name": "Home mobility", "type": "habit", "duration": "15m",
                                    "mini_of": "Gym session", "completion_dates": ["2026-04-14", "2026-04-15"]},
            "commitments/c.yml": _commitment(),
        }
        self.assertEqual(self._load(files)["commitments"][0]["progress"], 3)

    def test_completions_logged_in_the_daily_file_count(self):
        files = {
            "habits/gym.yml": _gym(),
            "commitments/c.yml": _commitment(),
            "schedules/completions/2026-04-14.yml": {"entries": {"Gym session@18:00": {"name": "Gym session", "status": "completed"}}},
            "schedules/completions/2026-04-15.yml": {"entries": {"Gym session@18:00": {"name": "Gym session", "status": "skipped"}}},
        }
        self.assertEqual(self._load(files)["commitments"][0]["progress"], 1)

    def test_interchangeable_targets_only_push_as_many_as_today_needs(self):
        files = {
            "habits/gym.yml": _gym(completion_dates=["2026-04-13", "2026-04-14"]),
            "habits/run.yml": {"name": "Run", "type": "habit", "duration": "30m"},
            "commitments/c.yml": _commitment(targets=[{"type": "habit", "name": "Gym session"}, {"type": "habit", "name": "Run"}]),
        }
        signals = self._load(files, SUNDAY)["by_identity"]    # 1 to do, last day
        self.assertEqual(signals["habit:gym session"]["commitment"]["level"], 1.0)
        self.assertEqual(signals["habit:run"]["commitment"]["level"], 0.2)

    def test_goal_level_combines_priority_and_closeness(self):
        files = {
            "goals/ship.yml": {"name": "Ship it", "type": "goal", "priority": "high", "due_date": "2026-04-18"},
            "goals/someday.yml": {"name": "Learn piano", "type": "goal", "priority": "low"},
            "goals/done.yml": {"name": "Old goal", "type": "goal", "status": "completed", "due_date": "2026-04-17"},
            "tasks/a.yml": {"name": "Write launch post", "type": "task", "goal": "Ship it"},
            "tasks/b.yml": {"name": "Practice scales", "type": "task", "goal": "Learn piano"},
            "tasks/c.yml": {"name": "Archive notes", "type": "task", "goal": "Old goal"},
        }
        signals = self._load(files)["by_identity"]
        self.assertAlmostEqual(signals["task:write launch post"]["goal"]["level"], 0.9)   # 0.35 + 0.55
        self.assertAlmostEqual(signals["task:practice scales"]["goal"]["level"], 0.105)   # 0.35 * 0.3
        self.assertNotIn("task:archive notes", signals)

    def test_goal_links_through_supporting_habits_milestones_and_projects(self):
        files = {
            "goals/fit.yml": {"name": "Get fit", "type": "goal", "priority": "medium", "due_date": "2026-06-30",
                              "supporting_habits": ["Gym session"]},
            "milestones/m.yml": {"name": "Run 5k", "type": "milestone", "goal": "Get fit", "due_date": "2026-04-20",
                                 "criteria": {"count": {"of": {"type": "habit", "name": "Run"}, "times": 10}}},
            "projects/p.yml": {"name": "Home gym", "type": "project", "goal": "Get fit"},
            "habits/gym.yml": _gym(),
            "habits/run.yml": {"name": "Run", "type": "habit", "duration": "30m"},
            "tasks/t.yml": {"name": "Order dumbbells", "type": "task", "project": "Home gym"},
        }
        signals = self._load(files)["by_identity"]
        self.assertEqual(signals["habit:gym session"]["goal"]["via"], "supporting habit")
        self.assertEqual(signals["task:order dumbbells"]["goal"]["via"], 'project "Home gym"')
        # The milestone's nearer date (4 days) drives the urgency, not the goal's.
        self.assertEqual(signals["habit:run"]["goal"]["days_left"], 4)
        self.assertGreater(signals["habit:run"]["goal"]["level"], signals["habit:gym session"]["goal"]["level"])

    def test_weights_scale_and_switch_off_the_bonus(self):
        signal = {"goal": {"level": 1.0}, "commitment": {"level": 1.0}}
        self.assertEqual(Direction.bonus_for(signal), 150.0)            # 60 + 90
        self.assertEqual(Direction.bonus_for(signal, {"goal_alignment": 10, "commitment_pressure": 5}), 210.0)
        self.assertEqual(Direction.bonus_for(signal, {"goal_alignment": 0, "commitment_pressure": 0}), 0.0)
        self.assertEqual(Direction.bonus_for(None), 0.0)


def _run(files, *, status=None, day=None):
    """Run Kairos on the fixture with a plain day (sleep anchor only) plus `files`."""
    with temporary_kairos_user_fixture() as fixture:
        user_dir = fixture["user_dir"]
        days_dir = os.path.join(user_dir, "days")
        for name in os.listdir(days_dir):
            os.remove(os.path.join(days_dir, name))
        _write(os.path.join(days_dir, "plain_day.yml"), day or PLAIN_DAY)
        _seed(user_dir, files)
        if status is not None:
            _write(os.path.join(user_dir, "profile", "current_status.yml"), status)
        result = KairosV2Scheduler({"now": NOW}).generate_schedule(NOW.date())
    return result.get("schedule", {})


def _placed(schedule):
    names = []
    for block in schedule.get("conceptual_schedule", {}).get("conceptual_blocks", []):
        names.append(block.get("name"))
        names.extend(child.get("name") for child in (block.get("children") or []))
    return names


def _candidate(schedule, name):
    for row in schedule.get("reality_filtered_candidates", {}).get("candidates", []):
        if row.get("name") == name:
            return row
    return None


class DirectionInTheSchedule(unittest.TestCase):
    def test_a_task_with_no_date_is_scheduled_once_it_serves_a_goal(self):
        task = {"name": "Write launch post", "type": "task", "duration": "45m"}
        without = _run({"tasks/a.yml": task})
        self.assertNotIn("Write launch post", _placed(without))

        with_goal = _run({
            "tasks/a.yml": {**task, "goal": "Ship it"},
            "goals/ship.yml": {"name": "Ship it", "type": "goal", "priority": "high", "due_date": "2026-04-18"},
        })
        self.assertIn("Write launch post", _placed(with_goal))
        self.assertIn("serves_active_goal", _candidate(with_goal, "Write launch post")["reasons"])

    def test_a_habit_not_due_today_is_scheduled_when_its_commitment_needs_it(self):
        gym = _gym(frequency="monday")   # its own rhythm would skip Thursday
        without = _run({"habits/gym.yml": gym})
        self.assertNotIn("Gym session", _placed(without))

        with_commitment = _run({"habits/gym.yml": gym, "commitments/c.yml": _commitment()})
        self.assertIn("Gym session", _placed(with_commitment))
        self.assertIn("commitment_needs_progress", _candidate(with_commitment, "Gym session")["reasons"])
        pushed = {row["identity"]: row for row in with_commitment["direction"]["pushed_items"]}
        self.assertEqual(pushed["habit:gym session"]["bonus"], 63.0)   # 90 * 0.7

    def test_a_met_commitment_does_not_add_the_habit(self):
        schedule = _run({
            "habits/gym.yml": _gym(frequency="monday", completion_dates=["2026-04-13", "2026-04-14", "2026-04-15"]),
            "commitments/c.yml": _commitment(),
        })
        self.assertNotIn("Gym session", _placed(schedule))


ENERGY = {"settings/energy_settings.yml": {"Energy_Settings": {
    "High": {"value": 1}, "Medium": {"value": 2}, "Low": {"value": 3}, "Exhausted": {"value": 4}}}}
GYM_NEEDS_ENERGY = _gym(frequency="daily", status_requirements={"energy": ["high", "medium"]})
MOBILITY = {"name": "Home mobility", "type": "habit", "duration": "15m", "mini_of": "Gym session"}


class ScaleDownForStatus(unittest.TestCase):
    def test_low_energy_day_swaps_in_the_mini_and_keeps_the_commitment_push(self):
        schedule = _run(
            {**ENERGY, "habits/gym.yml": GYM_NEEDS_ENERGY, "habits/mobility.yml": MOBILITY,
             "commitments/c.yml": _commitment()},
            status={"energy": "low"},
        )
        placed = _placed(schedule)
        self.assertIn("Home mobility", placed)
        self.assertNotIn("Gym session", placed)
        mini = _candidate(schedule, "Home mobility")
        self.assertEqual(mini["scaled_down_from"]["name"], "Gym session")
        self.assertEqual(mini["direction"]["commitment"]["name"], "Three workouts a week")
        swaps = schedule["reality_filtered_candidates"]["scaled_down"]
        self.assertEqual([(row["from"], row["to"]) for row in swaps], [("Gym session", "Home mobility")])
        self.assertEqual(placed.count("Home mobility"), 1)
        self.assertGreater(swaps[0]["status_distance"], swaps[0]["mini_status_distance"])

    def test_a_day_that_fits_keeps_the_full_version(self):
        schedule = _run(
            {**ENERGY, "habits/gym.yml": GYM_NEEDS_ENERGY, "habits/mobility.yml": MOBILITY},
            status={"energy": "high"},
        )
        placed = _placed(schedule)
        self.assertIn("Gym session", placed)
        self.assertNotIn("Home mobility", placed)

    def test_a_mini_that_is_also_a_daily_habit_is_not_scheduled_beside_the_full_version(self):
        schedule = _run(
            {**ENERGY, "habits/gym.yml": GYM_NEEDS_ENERGY,
             "habits/mobility.yml": {**MOBILITY, "frequency": "daily"}},
            status={"energy": "high"},
        )
        placed = _placed(schedule)
        self.assertIn("Gym session", placed)
        self.assertNotIn("Home mobility", placed)
        self.assertEqual(
            schedule["reality_filtered_candidates"]["scaled_down"],
            [{"from": "Home mobility", "to": None, "reason": "full_version_is_scheduled"}],
        )

    def test_last_chance_commitment_outranks_an_ordinary_task_due_today(self):
        schedule = _run({
            "habits/gym.yml": _gym(),
            "commitments/c.yml": _commitment(times=1, period="day"),
            "tasks/report.yml": {"name": "Write report", "type": "task", "duration": "60m",
                                 "priority": "High", "category": "Work", "due_date": THURSDAY.isoformat()},
        })
        placed = _placed(schedule)
        self.assertLess(placed.index("Gym session"), placed.index("Write report"))

    def test_without_a_mini_the_item_stays_as_it_is(self):
        schedule = _run({**ENERGY, "habits/gym.yml": GYM_NEEDS_ENERGY}, status={"energy": "low"})
        self.assertIn("Gym session", _placed(schedule))


class CommitmentTrackerAgrees(unittest.TestCase):
    def test_tracker_reads_capitalised_rule_and_counts_the_mini(self):
        from modules.commitment import main as Commitment
        with temporary_kairos_user_fixture() as fixture:
            _seed(fixture["user_dir"], {
                "habits/gym_session.yml": _gym(completion_dates=[THURSDAY.isoformat()]),
                "habits/home_mobility.yml": {**MOBILITY, "completion_dates": ["2026-04-14"]},
            })
            original_count = Commitment._count_in_period
            # The tracker counts against the real clock; pin it to the fixture's week.
            Commitment._count_in_period = lambda dates, period: sum(
                1 for d in dates if "2026-04-13" <= d <= "2026-04-19")
            try:
                status = Commitment.get_commitment_status(_commitment(), today=THURSDAY)
            finally:
                Commitment._count_in_period = original_count
        self.assertEqual((status["kind"], status["times"], status["period"]), ("frequency", 3, "week"))
        self.assertEqual(status["progress"], 2)


if __name__ == "__main__":
    unittest.main()
