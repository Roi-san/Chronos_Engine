"""
The commitment tracker on the shared period helper (roadmap step 1c).

`modules/commitment/main.py` is what the Commitments widget, `commitments check`
and its triggers (rewards, achievements, scripts) use. Before step 1c it had its
own period code, read only an item's `completion_dates`, and counted against the
real clock even when given another day. See docs/scheduling/recurrence_design.md,
"Decisions after the proposal", point 8, and tracker issues 24 and 28.

Fixture week: Monday 13 to Sunday 19 April 2026; "today" is Thursday 16 April.
"""
import os
import sys
import unittest
from datetime import date

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from chronos_fixture import temporary_kairos_user_fixture  # noqa: E402
from modules.commitment import main as Commitment  # noqa: E402
from test_kairos_v2_direction import _commitment, _gym, _seed  # noqa: E402

THURSDAY = date(2026, 4, 16)


def _logged(day, name, status="completed"):
    """A completion as Start day (the timer) records it: only in the day's log."""
    return {f"schedules/completions/{day}.yml": {"entries": {f"{name}@18:00": {"name": name, "status": status}}}}


def _status(files, commitment, today=THURSDAY):
    with temporary_kairos_user_fixture() as fixture:
        _seed(fixture["user_dir"], files)
        return Commitment.get_commitment_status(commitment, today=today)


class TrackerCountsWhatTheSchedulerCounts(unittest.TestCase):
    def test_a_start_day_completion_counts(self):
        files = {"habits/gym_session.yml": _gym(), **_logged("2026-04-14", "Gym session")}
        self.assertEqual(_status(files, _commitment())["progress"], 1)

    def test_a_completion_in_both_places_counts_once(self):
        files = {"habits/gym_session.yml": _gym(completion_dates=["2026-04-14"]), **_logged("2026-04-14", "Gym session")}
        self.assertEqual(_status(files, _commitment())["progress"], 1)

    def test_the_lighter_versions_logged_completion_counts(self):
        files = {"habits/gym_session.yml": _gym(),
                 "habits/home_mobility.yml": {"name": "Home mobility", "type": "habit", "duration": "15m",
                                              "mini_of": "Gym session"},
                 **_logged("2026-04-15", "Home mobility")}
        self.assertEqual(_status(files, _commitment())["progress"], 1)

    def test_a_skip_in_the_log_does_not_count(self):
        files = {"habits/gym_session.yml": _gym(), **_logged("2026-04-14", "Gym session", status="skipped")}
        self.assertEqual(_status(files, _commitment())["progress"], 0)


class TrackerUsesTheDayItIsGiven(unittest.TestCase):
    def test_the_day_given_is_used_not_the_real_clock(self):
        files = {"habits/gym_session.yml": _gym(completion_dates=["2026-04-13", "2026-04-14", "2026-04-15"])}
        status = _status(files, _commitment())
        self.assertEqual(status["progress"], 3)
        self.assertTrue(status["met"])

    def test_last_week_does_not_count_for_this_week(self):
        files = {"habits/gym_session.yml": _gym(completion_dates=["2026-04-10", "2026-04-11", "2026-04-12"])}
        self.assertEqual(_status(files, _commitment())["progress"], 0)


class TrackerPeriods(unittest.TestCase):
    def test_quarter_and_year_periods(self):
        files = {"habits/gym_session.yml": _gym(completion_dates=["2025-12-30", "2026-03-30", "2026-04-02"])}
        self.assertEqual(_status(files, _commitment(times=2, period="quarter"))["progress"], 1)   # Q2: 2 April
        self.assertEqual(_status(files, _commitment(times=2, period="year"))["progress"], 2)      # 2026

    def test_two_completions_on_one_day_still_count_twice(self):
        # Unchanged on purpose (issue 28): the tracker counts completions, the scheduler counts days.
        files = {"habits/gym_session.yml": _gym(completion_dates=["2026-04-14", "2026-04-14"])}
        commitment = _commitment(targets=[{"type": "habit", "name": "Gym session", "count": 2}])
        status = _status(files, commitment)
        self.assertEqual(status["progress"], 2)
        self.assertTrue(status["met"])

    def test_period_keys_are_unchanged(self):
        self.assertEqual(Commitment._period_key(THURSDAY, "week"), "2026-W16")
        self.assertEqual(Commitment._period_key(THURSDAY, "month"), "2026-04")
        self.assertEqual(Commitment._period_key(THURSDAY, "day"), "2026-04-16")
        self.assertEqual(Commitment._period_key(THURSDAY, "quarter"), "2026-Q2")
        self.assertEqual(Commitment._period_key(THURSDAY, "year"), "2026")
        self.assertEqual(Commitment._period_key(THURSDAY, "fortnight"), "2026-04-16")   # unknown: a day key, as before


if __name__ == "__main__":
    unittest.main()
