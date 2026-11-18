"""
Recurring items through Kairos (roadmap step 1c, decision D2; issue 10).
Design and the exact rule: docs/scheduling/recurrence_design.md. The rules on
their own are tested in test_recurrence.py; here Kairos plans real days.

Before this step `weekly` was planned every day and `monthly` / `quarterly` /
`yearly` never. Daily and weekday items must not change.

The week used: Monday 13 to Sunday 19 April 2026 (the fixture's week).
"""
import os
import sys
import unittest
from datetime import date, datetime, timedelta
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from chronos_fixture import temporary_kairos_user_fixture  # noqa: E402
from modules.scheduler import direction as Direction  # noqa: E402
from modules.scheduler.kairos_v2 import KairosV2Scheduler  # noqa: E402
from test_kairos_v2_direction import PLAIN_DAY, SLEEP, _commitment, _placed, _seed, _write  # noqa: E402
from test_kairos_v2_status_scale_down import LOW, PRIORITIES, SCALES, _status_settings, needs  # noqa: E402

MON, TUE, WED, THU, FRI, SAT, SUN = (date(2026, 4, 13) + timedelta(days=i) for i in range(7))
WEEK = [MON, TUE, WED, THU, FRI, SAT, SUN]
WIZARD_WEEKLY = ["Laundry", "Vacuum Floors", "Clean Bathroom", "Change Bed Sheets",
                 "Take Out Trash and Recycling", "Mop Floors", "Water Houseplants"]
WIZARD_MONTHLY = ["Deep Clean Fridge", "Clean Microwave and Oven", "Dust Fans and Baseboards",
                  "Wash Windows", "Clean Shower Drain", "Organize Pantry"]
HELPER_WINDOWS = {"Deadline Window", "Due Window", "Commitment Window", "Goal Window", "Manual Opportunity Window"}


def _slug(name):
    return name.lower().replace(" ", "_")


def _chore(name, frequency="weekly", **extra):
    return {f"habits/{_slug(name)}.yml": {"name": name, "type": "habit", "duration": "15m",
                                          "frequency": frequency, "chore": True, **extra}}


def _run(day, files, *, status=None, template=None, hour=8):
    """Plan `day` at `hour`:00 on a plain day (a sleep anchor only) plus `files`."""
    now = datetime(day.year, day.month, day.day, hour, 0)
    with temporary_kairos_user_fixture() as fixture:
        user_dir = fixture["user_dir"]
        days_dir = os.path.join(user_dir, "days")
        for name in os.listdir(days_dir):
            os.remove(os.path.join(days_dir, name))
        _write(os.path.join(days_dir, "plain_day.yml"), template or PLAIN_DAY)
        _seed(user_dir, files)
        if status is not None:
            _write(os.path.join(user_dir, "profile", "current_status.yml"), status)
        result = KairosV2Scheduler({"now": now}).generate_schedule(day)
    return result.get("schedule", {})


def _universe(schedule):
    return {row.get("name") for row in schedule.get("candidate_universe", {}).get("candidates", [])}


def _recurring(schedule, name):
    for row in (schedule.get("recurring") or {}).get("items", []):
        if row.get("name") == name:
            return row
    return None


def _bonus(schedule, identity):
    for row in (schedule.get("direction") or {}).get("pushed_items", []):
        if row.get("identity") == identity:
            return row.get("bonus")
    return None


def _days_planned(files, name, days=WEEK):
    return [day for day in days if name in _placed(_run(day, files))]


class OncePerWeek(unittest.TestCase):
    def test_an_undated_weekly_item_waits_for_its_turn_then_stays_until_done(self):
        # One undated weekly item: its turn is Thursday. Before D2 it was on every day.
        self.assertEqual(_days_planned(_chore("Laundry"), "Laundry"), [THU, FRI, SAT, SUN])

    def test_a_picked_day_is_kept_and_a_missed_one_comes_back(self):
        self.assertEqual(_days_planned(_chore("Laundry", day="saturday"), "Laundry"), [SAT, SUN])

    def test_done_on_its_day_means_gone_until_next_week(self):
        files = _chore("Laundry", day="saturday", completion_dates=[SAT.isoformat()])
        self.assertNotIn("Laundry", _placed(_run(SUN, files)))
        self.assertIn("Laundry", _placed(_run(SAT + timedelta(days=7), files)))

    def test_done_before_its_day_counts_for_the_week(self):
        files = _chore("Laundry", day="saturday", completion_dates=[WED.isoformat()])
        self.assertNotIn("Laundry", _placed(_run(SAT, files)))

    def test_a_completion_logged_by_start_day_counts(self):
        # The timer (Start day) writes only the day's completion log, not the item's history.
        files = {**_chore("Laundry", day="saturday"),
                 f"schedules/completions/{SAT.isoformat()}.yml": {"entries": {
                     "Laundry@09:00": {"name": "Laundry", "status": "completed"}}}}
        self.assertNotIn("Laundry", _placed(_run(SUN, files)))


class NoWallOfChores(unittest.TestCase):
    def test_the_wizards_seven_weekly_chores_get_one_day_each(self):
        files = {}
        for name in WIZARD_WEEKLY:
            files.update(_chore(name))
        schedule = _run(MON, files)
        turns = {name: _recurring(schedule, name)["turn"] for name in WIZARD_WEEKLY}
        self.assertEqual(sorted(turns.values()), [day.isoformat() for day in WEEK])
        # Each chore done on its turn: every day has exactly one weekly chore.
        for day in WEEK:
            seeded = {}
            for name in WIZARD_WEEKLY:
                done = [turns[name]] if turns[name] < day.isoformat() else []
                seeded.update(_chore(name, completion_dates=done))
            weekly_today = _universe(_run(day, seeded)) & set(WIZARD_WEEKLY)
            self.assertEqual(len(weekly_today), 1, (day, weekly_today))

    def test_setting_up_every_chore_mid_week_does_not_pile_up_missed_ones(self):
        # The wizard's 7 weekly and 6 monthly chores, set up on Thursday 16 April. Weekly
        # turns run Monday to Sunday in name order; monthly ones are the 3rd, 8th, 13th, ...
        def chores(**extra):
            files = {}
            for name in WIZARD_WEEKLY:
                files.update(_chore(name, **extra))
            for name in WIZARD_MONTHLY:
                files.update(_chore(name, "monthly", **extra))
            return files
        stamped = _run(THU, chores(created=THU.isoformat()))
        self.assertEqual(stamped["recurring"]["due_today"], ["Mop Floors"])     # only today's turn
        # Without a creation date, every passed turn counts as missed (7 at once): the
        # reason new items get `created` (design decision 9).
        self.assertEqual(len(_run(THU, chores())["recurring"]["due_today"]), 7)

    def test_a_picked_day_is_not_doubled_up(self):
        files = _chore("Laundry", day="saturday")
        for name in WIZARD_WEEKLY[1:]:
            files.update(_chore(name))
        schedule = _run(MON, files)
        turns = [_recurring(schedule, name)["turn"] for name in WIZARD_WEEKLY]
        self.assertEqual(len(set(turns)), 7)
        self.assertEqual(_recurring(schedule, "Laundry")["turn"], SAT.isoformat())
        self.assertEqual(_recurring(schedule, "Laundry")["turn_source"], "picked")

    def test_the_wizards_monthly_chores_are_spread_over_the_month(self):
        files = {}
        for name in WIZARD_MONTHLY:
            files.update(_chore(name, "monthly"))
        schedule = _run(MON, files)
        turns = sorted(_recurring(schedule, name)["turn"] for name in WIZARD_MONTHLY)
        self.assertEqual(turns, [f"2026-04-{d:02d}" for d in (3, 8, 13, 18, 23, 28)])


class LongerPeriods(unittest.TestCase):
    def test_monthly_quarterly_and_yearly_items_are_planned_on_their_turn(self):
        # Before D2 none of these was ever planned. Alone in their period, their turns are
        # 16 April (April has 30 days), 16 May (Q2 has 91) and 2 July (2026 has 365).
        cases = [("Wash Windows", "monthly", date(2026, 4, 16)),
                 ("Replace Filter", "quarterly", date(2026, 5, 16)),
                 ("Test Smoke Alarms", "yearly", date(2026, 7, 2))]
        for name, frequency, turn in cases:
            files = _chore(name, frequency)
            self.assertNotIn(name, _placed(_run(turn - timedelta(days=1), files)), name)
            self.assertIn(name, _placed(_run(turn, files)), name)

    def test_a_monthly_item_with_a_day(self):
        files = _chore("Wash Windows", "monthly", day=20)
        self.assertNotIn("Wash Windows", _placed(_run(THU, files)))
        self.assertIn("Wash Windows", _placed(_run(date(2026, 4, 20), files)))

    def test_done_this_month_means_not_again_this_month(self):
        files = _chore("Wash Windows", "monthly", completion_dates=["2026-04-02"])
        self.assertNotIn("Wash Windows", _placed(_run(THU, files)))
        self.assertIn("Wash Windows", _placed(_run(date(2026, 5, 16), files)))   # May 16: its May turn


class DailyAndFixedDaysUnchanged(unittest.TestCase):
    def test_daily_every_day_and_weekday_items_only_on_their_days(self):
        files = {**_chore("Wash Dishes", "daily"), **_chore("Board Games", "tuesday")}
        for day in (MON, TUE, WED):
            placed = _placed(_run(day, files))
            self.assertIn("Wash Dishes", placed, day)
            self.assertEqual("Board Games" in placed, day == TUE, day)   # missed Tuesday: not carried over


class Pressure(unittest.TestCase):
    def test_the_push_grows_as_the_week_runs_out(self):
        files = _chore("Laundry")
        rows = []
        for day in (THU, FRI, SAT, SUN):
            schedule = _run(day, files)
            rows.append((_recurring(schedule, "Laundry")["state"], _recurring(schedule, "Laundry")["level"],
                         _bonus(schedule, "habit:laundry")))
        self.assertEqual(rows, [("on_track", 0.2, 4.8), ("tightening", 0.45, 10.8),
                                ("at_risk", 0.7, 16.8), ("last_chance", 1.0, 24.0)])

    def _priorities(self, rank):
        return {"settings/scheduling_priorities.yml": {"Scheduling_Priorities": [
            {"Name": "Recurring Pressure", "Order": 1, "Rank": rank}]}}

    def test_the_recurring_pressure_dial(self):
        doubled = _run(SAT, {**_chore("Laundry"), **self._priorities(10)})
        self.assertEqual(_bonus(doubled, "habit:laundry"), 33.6)
        off = _run(SAT, {**_chore("Laundry"), **self._priorities(0)})
        self.assertEqual(_bonus(off, "habit:laundry"), 0.0)
        self.assertIn("Laundry", _placed(off))          # 0 switches the push off, not the item

    def test_a_missed_daily_item_gets_a_small_push(self):
        missed = _run(THU, _chore("Wash Dishes", "daily", completion_dates=["2026-04-10"]))
        self.assertEqual(_bonus(missed, "habit:wash dishes"), 4.8)
        self.assertEqual(_recurring(missed, "Wash Dishes")["reason"], "Daily: missed yesterday.")
        kept_up = _run(THU, _chore("Wash Dishes", "daily", completion_dates=["2026-04-15"]))
        self.assertIsNone(_bonus(kept_up, "habit:wash dishes"))

    def test_it_counts_as_importance_never_as_urgency(self):
        # Needs high energy, today is low: 2 steps short, 1 beyond grace, strain 0.71.
        files = {**_status_settings(), **SCALES, **PRIORITIES, **_chore("Clean Garage", **needs(energy="high"))}
        sunday = _run(SUN, files, status=LOW)            # last chance: importance 1.0 keeps it
        kept = {row["name"]: row for row in sunday["status_scale_down"]["kept"]}
        self.assertEqual(kept["Clean Garage"]["kind"], "important")
        self.assertIn("recurring", [s["source"] for s in kept["Clean Garage"]["importance_sources"]])
        thursday = _run(THU, files, status=LOW)          # on track: 0.2 does not outweigh the strain
        self.assertIn("Clean Garage", [row["name"] for row in thursday["status_scale_down"]["saved"]])

    def test_it_never_opens_a_helper_window(self):
        schedule = _run(SUN, _chore("Laundry"))
        for block in schedule.get("conceptual_schedule", {}).get("conceptual_blocks", []):
            if "Laundry" in [child.get("name") for child in (block.get("children") or [])]:
                self.assertNotIn(block.get("name"), HELPER_WINDOWS)


class WorksWithTheRest(unittest.TestCase):
    def test_a_commitment_still_brings_its_target_back(self):
        # Gym is weekly and was done on Monday, but "3 workouts a week" needs two more.
        files = {"habits/gym.yml": {"name": "Gym session", "type": "habit", "duration": "60m",
                                    "frequency": "weekly", "completion_dates": [MON.isoformat()]},
                 "commitments/c.yml": _commitment()}
        schedule = _run(THU, files)
        self.assertEqual(_recurring(schedule, "Gym session")["state"], "done")
        self.assertIn("Gym session", _placed(schedule))

    def test_the_lighter_version_counts_as_done(self):
        files = {**_chore("Clean Bathroom"),
                 "habits/quick_wipe.yml": {"name": "Quick wipe", "type": "habit", "duration": "5m",
                                           "mini_of": "Clean Bathroom", "completion_dates": [WED.isoformat()]}}
        self.assertNotIn("Clean Bathroom", _placed(_run(THU, files)))

    def test_a_template_child_is_planned_whenever_its_template_is_used(self):
        template = {"name": "Plain Day", "type": "day", "children": [
            SLEEP, {"name": "Laundry", "type": "habit", "duration": "15m", "frequency": "weekly"}]}
        self.assertIn("Laundry", _placed(_run(MON, {}, template=template)))


class Record(unittest.TestCase):
    def test_every_once_per_period_item_and_every_unknown_frequency_is_recorded(self):
        files = {**_chore("Laundry"), **_chore("Wash Windows", "monthly", day=20), **_chore("Odd One", "biweekly")}
        schedule = _run(MON, files)
        laundry = _recurring(schedule, "Laundry")
        self.assertEqual((laundry["due"], laundry["state"], laundry["turn"], laundry["turn_source"]),
                         (False, "waiting", THU.isoformat(), "spread"))
        windows = _recurring(schedule, "Wash Windows")
        self.assertEqual((windows["turn"], windows["turn_source"]), ("2026-04-20", "picked"))
        self.assertEqual(schedule["recurring"]["unrecognised"],
                         [{"identity": "habit:odd one", "name": "Odd One", "frequency": "biweekly"}])
        # Short lines for people: the same ones go into the decision log's notes.
        self.assertEqual(schedule["recurring"]["waiting"],
                         ["Laundry: its turn is Thursday 16 April", "Wash Windows: its day is Monday 20 April"])
        self.assertEqual(schedule["recurring"]["due_today"], [])

    def test_if_history_cannot_be_read_periodic_items_are_shown(self):
        with mock.patch.object(Direction, "load_direction", side_effect=RuntimeError("disk on fire")):
            schedule = _run(MON, _chore("Laundry"))
        self.assertIn("Laundry", _placed(schedule))      # visible, never hidden
        self.assertEqual(schedule["recurring"]["fallback"], ["Laundry"])


if __name__ == "__main__":
    unittest.main()
