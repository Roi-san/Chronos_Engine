"""
Recurring items, the rules on their own (roadmap step 1c, decision D2):
`modules/scheduler/recurrence.py`, docs/scheduling/recurrence_design.md,
"The rule as built". Kairos itself is tested in test_kairos_v2_recurrence.py.

The week used throughout: Monday 16 to Sunday 22 November 2026.
"""
import os
import random
import shutil
import sys
import tempfile
import unittest
from datetime import date, timedelta

import yaml

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from modules.scheduler import recurrence as Recurrence  # noqa: E402

MON, TUE, WED, THU, FRI, SAT, SUN = (date(2026, 11, 16) + timedelta(days=i) for i in range(7))
WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _old_applies(frequency, target_date):
    """kairos_v2._frequency_applies_to_date before step 1c (frozen copy, the reference for daily and weekdays)."""
    token = lambda v: str(v or "").strip().lower().replace(" ", "_").replace("-", "_")
    if frequency is None:
        return False
    weekday = target_date.strftime("%A").lower()
    if isinstance(frequency, list):
        tokens = [token(value) for value in frequency]
    else:
        text = str(frequency).strip().lower()
        if not text:
            return False
        tokens = [token(t) for t in text.replace("/", ",").split(",")]
    tokens = [t for t in tokens if t]
    if not tokens:
        return False
    if "daily" in tokens or "weekly" in tokens:
        return True
    return weekday in tokens


def _entries(*names, day=None):
    return [{"identity": f"habit:{name.lower()}", "name": name, "day": day} for name in names]


def _turns(entries, period, any_day):
    return {identity: row["turn"] for identity, row in Recurrence.spread_turns(entries, period, any_day).items()}


class ParseFrequency(unittest.TestCase):
    def test_daily(self):
        for value in ("daily", "Daily", ["daily"], "DAILY "):
            self.assertEqual(Recurrence.parse_frequency(value)["rhythm"], "daily", value)

    def test_weekday_names(self):
        info = Recurrence.parse_frequency("monday, thursday")
        self.assertEqual((info["rhythm"], info["weekdays"]), ("weekdays", ["monday", "thursday"]))
        self.assertEqual(Recurrence.parse_frequency("Monday/Friday")["weekdays"], ["monday", "friday"])
        self.assertEqual(Recurrence.parse_frequency(["Tuesday"])["weekdays"], ["tuesday"])

    def test_once_per_period(self):
        for value, period in (("weekly", "week"), ("Monthly", "month"), ("quarterly", "quarter"), ("YEARLY", "year")):
            info = Recurrence.parse_frequency(value)
            self.assertEqual((info["rhythm"], info["period"]), ("period", period), value)

    def test_daily_wins_then_the_first_period_then_weekdays(self):
        self.assertEqual(Recurrence.parse_frequency("weekly, daily")["rhythm"], "daily")
        info = Recurrence.parse_frequency("monday, weekly, monthly")
        self.assertEqual((info["rhythm"], info["period"]), ("period", "week"))
        self.assertEqual(info["ignored"], ["monday", "monthly"])

    def test_values_it_does_not_understand(self):
        for value in ("biweekly", "every day", "mon", "weekdays", "3x a week"):
            self.assertEqual(Recurrence.parse_frequency(value)["rhythm"], "unknown", value)

    def test_nothing(self):
        for value in (None, "", [], "  "):
            self.assertEqual(Recurrence.parse_frequency(value)["rhythm"], "none", value)


class DailyAndWeekdaysUnchanged(unittest.TestCase):
    """Only weekly to yearly change with D2. Daily and weekday items are planned exactly as before."""

    def test_same_days_as_before_d2(self):
        values = ["daily", "Daily", ["daily"], "monday", "Monday, Thursday", "monday/friday", ["Tuesday", "saturday"],
                  "sunday", "biweekly", "mon", "every day", "", None, "daily, monday"]
        for value in values:
            info = Recurrence.parse_frequency(value)
            for day in (MON, TUE, WED, THU, FRI, SAT, SUN):
                due = Recurrence.evaluate(info, day, set())["due"] if info["rhythm"] != "none" else False
                self.assertEqual(due, _old_applies(value, day), (value, day))


class PreferredDay(unittest.TestCase):
    def test_a_weekday_for_weekly_items(self):
        for value in ("saturday", "Sat", "SATURDAY", " sat "):
            self.assertEqual(Recurrence.preferred_day(value, "week", WED), (SAT, None), value)

    def test_a_day_of_the_month_for_monthly_items(self):
        self.assertEqual(Recurrence.preferred_day(15, "month", WED), (date(2026, 11, 15), None))
        self.assertEqual(Recurrence.preferred_day("15", "month", WED), (date(2026, 11, 15), None))

    def test_a_day_the_month_does_not_have_means_its_last_day(self):
        self.assertEqual(Recurrence.preferred_day(31, "month", WED)[0], date(2026, 11, 30))
        self.assertEqual(Recurrence.preferred_day(31, "month", date(2027, 2, 10))[0], date(2027, 2, 28))
        self.assertEqual(Recurrence.preferred_day(30, "month", date(2028, 2, 10))[0], date(2028, 2, 29))

    def test_no_day(self):
        self.assertEqual(Recurrence.preferred_day(None, "week", WED), (None, None))
        self.assertEqual(Recurrence.preferred_day("", "month", WED), (None, None))

    def test_a_day_that_does_not_fit_is_ignored_and_said_why(self):
        for value, period in (("funday", "week"), (15, "week"), ("saturday", "month"), (0, "month"), (40, "month"),
                              ("march 3", "year"), (10, "quarter")):
            turn, problem = Recurrence.preferred_day(value, period, WED)
            self.assertIsNone(turn, (value, period))
            self.assertTrue(problem, (value, period))


class SpreadTurns(unittest.TestCase):
    def test_weekly_items_are_spaced_over_the_week(self):
        self.assertEqual(list(_turns(_entries("A"), "week", WED).values()), [THU])
        self.assertEqual(sorted(_turns(_entries("A", "B"), "week", WED).values()), [TUE, SAT])
        self.assertEqual(sorted(_turns(_entries("A", "B", "C"), "week", WED).values()), [TUE, THU, SAT])
        self.assertEqual(sorted(_turns(_entries("A", "B", "C", "D"), "week", WED).values()), [MON, WED, FRI, SUN])

    def test_seven_weekly_chores_get_one_day_each_in_name_order(self):
        names = ["Water Houseplants", "Laundry", "Vacuum Floors", "Mop Floors", "Clean Bathroom",
                 "Change Bed Sheets", "Take Out Trash and Recycling"]
        turns = _turns(_entries(*names), "week", WED)
        in_order = [turns[f"habit:{name.lower()}"] for name in sorted(names, key=str.lower)]
        self.assertEqual(in_order, [MON, TUE, WED, THU, FRI, SAT, SUN])

    def test_the_same_turns_on_every_day_of_the_period_and_in_any_input_order(self):
        entries = _entries("Laundry", "Vacuum", "Mop", "Bathroom")
        expected = _turns(entries, "week", MON)
        for day in (TUE, SUN):
            self.assertEqual(_turns(entries, "week", day), expected)
        shuffled = list(entries)
        random.Random(7).shuffle(shuffled)
        self.assertEqual(_turns(shuffled, "week", WED), expected)

    def test_monthly_quarterly_and_yearly(self):
        six = _entries("A", "B", "C", "D", "E", "F")
        self.assertEqual(sorted(_turns(six, "month", WED).values()),
                         [date(2026, 11, d) for d in (3, 8, 13, 18, 23, 28)])
        self.assertEqual(sorted(_turns(six, "month", date(2027, 2, 10)).values()),
                         [date(2027, 2, d) for d in (3, 8, 12, 17, 22, 26)])
        four = _entries("A", "B", "C", "D")
        self.assertEqual(sorted(_turns(four, "quarter", WED).values()),
                         [date(2026, 10, 12), date(2026, 11, 4), date(2026, 11, 27), date(2026, 12, 20)])
        self.assertEqual(sorted(_turns(four, "year", WED).values()),
                         [date(2026, 2, 15), date(2026, 5, 17), date(2026, 8, 17), date(2026, 11, 16)])
        self.assertEqual(list(_turns(_entries("A"), "month", WED).values()), [date(2026, 11, 16)])

    def test_a_picked_day_is_kept_and_not_doubled_up(self):
        entries = _entries("Laundry", day="saturday") + _entries("A", "B", "C", "D", "E", "F")
        spread = Recurrence.spread_turns(entries, "week", WED)
        self.assertEqual((spread["habit:laundry"]["turn"], spread["habit:laundry"]["source"]), (SAT, "picked"))
        turns = [row["turn"] for row in spread.values()]
        self.assertEqual(sorted(turns), [MON, TUE, WED, THU, FRI, SAT, SUN])
        self.assertTrue(all(row["source"] == "spread" for key, row in spread.items() if key != "habit:laundry"))

    def test_a_day_that_does_not_fit_counts_as_no_day(self):
        spread = Recurrence.spread_turns(_entries("Laundry", day="funday"), "week", WED)
        self.assertEqual((spread["habit:laundry"]["turn"], spread["habit:laundry"]["source"]), (THU, "spread"))
        self.assertTrue(spread["habit:laundry"]["day_problem"])

    def test_more_items_than_days_share_days_evenly(self):
        turns = _turns(_entries(*[f"Chore {i}" for i in range(9)]), "week", WED)
        per_day = {}
        for turn in turns.values():
            per_day[turn] = per_day.get(turn, 0) + 1
        self.assertEqual(len(per_day), 7)
        self.assertEqual(max(per_day.values()), 2)

    def test_same_name_different_types_both_get_turns(self):
        entries = [{"identity": "habit:laundry", "name": "Laundry", "day": None},
                   {"identity": "task:laundry", "name": "Laundry", "day": None}]
        self.assertEqual(sorted(_turns(entries, "week", WED).values()), [TUE, SAT])


class EvaluateOncePerPeriod(unittest.TestCase):
    WEEKLY = Recurrence.parse_frequency("weekly")

    def _eval(self, day, done=(), turn=THU, source="spread"):
        return Recurrence.evaluate(self.WEEKLY, day, set(done), turn=turn, turn_source=source)

    def test_before_its_turn_it_waits(self):
        status = self._eval(MON)
        self.assertEqual((status["due"], status["state"], status["level"]), (False, "waiting", 0.0))

    def test_from_its_turn_the_push_grows_as_the_week_runs_out(self):
        rows = [(self._eval(day)["state"], self._eval(day)["level"]) for day in (THU, FRI, SAT, SUN)]
        self.assertEqual(rows, [("on_track", 0.2), ("tightening", 0.45), ("at_risk", 0.7), ("last_chance", 1.0)])
        self.assertTrue(all(self._eval(day)["due"] for day in (THU, FRI, SAT, SUN)))

    def test_done_this_week_means_not_again_until_next_week(self):
        early = self._eval(FRI, done=[WED])          # done before its turn
        self.assertEqual((early["due"], early["state"], early["done_on"]), (False, "done", WED.isoformat()))
        self.assertFalse(self._eval(SAT, done=[FRI])["due"])
        self.assertFalse(self._eval(FRI, done=[FRI])["due"])

    def test_last_week_does_not_count_for_this_week(self):
        status = self._eval(THU, done=[date(2026, 11, 12)])
        self.assertTrue(status["due"])
        self.assertFalse(status["missed_previous"])
        self.assertEqual(status["level"], 0.2)

    def test_a_missed_previous_week_adds_a_small_push(self):
        status = self._eval(THU, done=[date(2026, 11, 5)])   # done two weeks ago, not last week
        self.assertTrue(status["missed_previous"])
        self.assertAlmostEqual(status["level"], 0.4)
        self.assertIn("missed last week too", status["reason"])
        self.assertEqual(self._eval(SUN, done=[date(2026, 11, 5)])["level"], 1.0)   # never above 1

    def test_a_brand_new_item_is_not_treated_as_missed(self):
        status = self._eval(THU)
        self.assertFalse(status["missed_previous"])

    def test_reasons(self):
        self.assertEqual(self._eval(THU)["reason"], "Once a week: today is its turn, 4 days left this week.")
        self.assertEqual(self._eval(SUN, turn=SAT, source="picked")["reason"],
                         "Once a week: missed its day (Saturday), last chance this week.")
        monthly = Recurrence.evaluate(Recurrence.parse_frequency("monthly"), date(2026, 11, 20), {date(2026, 9, 2)},
                                      turn=date(2026, 11, 13), turn_source="spread")
        self.assertEqual(monthly["reason"],
                         "Once a month: missed its turn (the 13th), 11 days left this month; missed last month too.")
        yearly = Recurrence.evaluate(Recurrence.parse_frequency("yearly"), date(2026, 11, 16), set(),
                                     turn=date(2026, 11, 16), turn_source="spread")
        self.assertEqual(yearly["reason"], "Once a year: today is its turn, 46 days left this year.")


class EvaluateDailyAndWeekdays(unittest.TestCase):
    DAILY = Recurrence.parse_frequency("daily")

    def test_a_daily_item_is_due_every_day_with_no_push_when_done_yesterday(self):
        status = Recurrence.evaluate(self.DAILY, THU, {WED, TUE})
        self.assertEqual((status["due"], status["level"], status["reason"]), (True, 0.0, None))

    def test_a_missed_day_gives_a_small_push_the_next_day(self):
        status = Recurrence.evaluate(self.DAILY, THU, {date(2026, 11, 10)})
        self.assertEqual((status["due"], status["state"], status["level"]), (True, "missed_yesterday", 0.2))
        self.assertEqual(status["reason"], "Daily: missed yesterday.")

    def test_never_done_means_no_push(self):
        self.assertEqual(Recurrence.evaluate(self.DAILY, THU, set())["level"], 0.0)

    def test_fixed_days_get_no_push_and_no_carry_over(self):
        info = Recurrence.parse_frequency("monday, thursday")
        self.assertEqual((Recurrence.evaluate(info, THU, set())["due"], Recurrence.evaluate(info, THU, set())["level"]), (True, 0.0))
        self.assertFalse(Recurrence.evaluate(info, TUE, set())["due"])      # Monday missed: gone until Thursday

    def test_unknown_values_are_never_due(self):
        status = Recurrence.evaluate(Recurrence.parse_frequency("biweekly"), THU, set())
        self.assertEqual((status["due"], status["state"]), (False, "unrecognised"))


class NewItems(unittest.TestCase):
    """
    Design decision 9: an item added after its turn has passed in this period was
    not "missed"; it starts with its next turn. Without this, setting up chores in
    the middle of a period put every chore whose turn had passed on the plan at
    once, marked "missed" (14 of the wizard's chores on a Thursday in November).
    """
    WEEKLY = Recurrence.parse_frequency("weekly")

    def test_added_after_its_turn_it_starts_with_its_next_turn(self):
        status = Recurrence.evaluate(self.WEEKLY, FRI, set(), turn=WED, turn_source="spread", created=THU)
        self.assertEqual((status["due"], status["state"], status["level"]), (False, "starts_next_period", 0.0))
        next_wednesday = WED + timedelta(days=7)
        self.assertTrue(Recurrence.evaluate(self.WEEKLY, next_wednesday, set(), turn=next_wednesday, created=THU)["due"])

    def test_added_on_or_before_its_turn_the_normal_rule_applies(self):
        self.assertTrue(Recurrence.evaluate(self.WEEKLY, WED, set(), turn=WED, created=WED)["due"])
        missed = Recurrence.evaluate(self.WEEKLY, FRI, set(), turn=WED, created=MON)   # missed: back until done
        self.assertEqual((missed["due"], missed["state"]), (True, "tightening"))

    def test_without_a_creation_date_a_passed_turn_counts(self):
        self.assertTrue(Recurrence.evaluate(self.WEEKLY, FRI, set(), turn=WED)["due"])

    def test_daily_and_weekday_items_do_not_look_at_it(self):
        later = FRI + timedelta(days=3)
        self.assertTrue(Recurrence.evaluate(Recurrence.parse_frequency("daily"), FRI, set(), created=later)["due"])
        self.assertTrue(Recurrence.evaluate(Recurrence.parse_frequency("friday"), FRI, set(), created=later)["due"])


class LoadRecurring(unittest.TestCase):
    def setUp(self):
        self.user_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.user_dir, ignore_errors=True)

    def _write(self, rel, payload):
        path = os.path.join(self.user_dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False)

    def test_reads_every_schedulable_folder_and_spreads_per_period(self):
        self._write("habits/laundry.yml", {"Name": "Laundry", "Frequency": "Weekly"})   # builder-style keys
        self._write("tasks/review.yml", {"name": "Review budget", "frequency": "weekly"})
        self._write("routines/reset.yml", {"name": "Sunday reset", "frequency": "weekly", "day": "sunday"})
        self._write("timeblocks/admin.yml", {"name": "Admin hour", "frequency": "monthly"})
        loaded = Recurrence.load_recurring(self.user_dir, WED)["by_identity"]
        self.assertEqual(loaded["habit:laundry"]["turn"], TUE.isoformat())
        self.assertEqual(loaded["task:review budget"]["turn"], SAT.isoformat())
        self.assertEqual((loaded["routine:sunday reset"]["turn"], loaded["routine:sunday reset"]["turn_source"]),
                         (SUN.isoformat(), "picked"))
        self.assertEqual(loaded["timeblock:admin hour"]["period"], "month")

    def test_paused_and_bad_items_take_no_turn(self):
        self._write("habits/a.yml", {"name": "A", "frequency": "weekly"})
        self._write("habits/b.yml", {"name": "B", "frequency": "weekly", "status": "paused"})
        self._write("habits/c.yml", {"name": "C", "frequency": "weekly", "polarity": "bad"})
        loaded = Recurrence.load_recurring(self.user_dir, WED)["by_identity"]
        self.assertEqual(set(loaded), {"habit:a"})
        self.assertEqual(loaded["habit:a"]["turn"], THU.isoformat())   # alone in its week

    def test_done_comes_from_history_logs_and_the_lighter_version(self):
        self._write("habits/a.yml", {"name": "A", "frequency": "weekly", "completion_dates": [MON.isoformat()]})
        self._write("habits/b.yml", {"name": "B", "frequency": "weekly"})
        self._write("habits/c.yml", {"name": "C", "frequency": "weekly"})
        self._write("habits/c_mini.yml", {"name": "C quick", "mini_of": "C", "completion_dates": [TUE.isoformat()]})
        self._write(f"schedules/completions/{MON.isoformat()}.yml",
                    {"entries": {"B@09:00": {"name": "B", "status": "completed"}}})
        loaded = Recurrence.load_recurring(self.user_dir, SUN)["by_identity"]
        self.assertEqual({key: row["state"] for key, row in loaded.items()},
                         {"habit:a": "done", "habit:b": "done", "habit:c": "done"})

    def test_the_creation_date_is_read(self):
        # Set up on Thursday: A's turn (Tuesday) has passed, B's (Saturday) has not.
        self._write("habits/a.yml", {"name": "A", "frequency": "weekly", "created": THU.isoformat()})
        self._write("habits/b.yml", {"name": "B", "frequency": "weekly", "created": THU.isoformat()})
        loaded = Recurrence.load_recurring(self.user_dir, THU)["by_identity"]
        self.assertEqual((loaded["habit:a"]["state"], loaded["habit:b"]["state"]), ("starts_next_period", "waiting"))

    def test_frequencies_it_does_not_understand_are_listed(self):
        self._write("habits/a.yml", {"name": "A", "frequency": "biweekly"})
        result = Recurrence.load_recurring(self.user_dir, WED)
        self.assertEqual(result["unrecognised"], [{"identity": "habit:a", "name": "A", "frequency": "biweekly"}])

    def test_inactive_statuses_match_what_kairos_skips(self):
        from modules.scheduler.kairos_v2 import KairosV2Scheduler
        scheduler = KairosV2Scheduler({})
        for status in sorted(Recurrence.INACTIVE_STATUSES) + ["active", "pending", "completed", ""]:
            self.assertEqual(status in Recurrence.INACTIVE_STATUSES,
                             scheduler._is_inactive_status({"status": status}), status)


if __name__ == "__main__":
    unittest.main()
