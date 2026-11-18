"""
Kairos v2 against a day authored the way the dashboard builders save it.

The Day Builder and Routine Builder write clock times as `ideal_start_time` /
`ideal_end_time`, put timed blocks under `children`, and files created from the
`*_defaults.yml` templates carry capitalised keys (`Name:`). Item durations are
written as `15m` / `1h30m`. These tests pin the behaviour that makes such a day
schedulable.
"""
import os
import sys
import unittest
from datetime import datetime

import yaml

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from chronos_fixture import temporary_kairos_user_fixture
from modules.scheduler.kairos_v2 import KairosV2Scheduler
from modules.scheduler.v1 import lowercase_top_level_keys, normalize_template_times

NOW = datetime(2026, 4, 16, 8, 0, 0)  # a Thursday morning

BUILDER_DAY = {
    "Name": "Builder Day",
    "Type": "day",
    "Sequence": [],
    "children": [
        {"type": "timeblock", "name": "Sleep", "duration": 480, "ideal_start_time": "23:30",
         "ideal_end_time": "07:30", "anchored": True, "reschedule": "never"},
        {"type": "window", "name": "Admin", "window": True, "duration": 90,
         "ideal_start_time": "10:00", "ideal_end_time": "11:30", "filters": {"tags": ["admin"]}},
        {"type": "timeblock", "name": "Lunch", "duration": 45, "ideal_start_time": "12:30",
         "ideal_end_time": "13:15", "anchored": True, "reschedule": "never"},
        {"type": "routine", "name": "Evening Wind Down", "duration": 30,
         "ideal_start_time": "21:30", "ideal_end_time": "22:00"},
    ],
}

# Tasks carry a due date because Kairos only considers recurring items and items
# with a due date or deadline (plus whatever the day template itself contains).
FILES = {
    os.path.join("routines", "evening_wind_down.yml"): {
        "Name": "Evening Wind Down", "Duration": 0,
        "children": [{"type": "task", "name": "Read 20 pages", "duration": 30}],
    },
    os.path.join("tasks", "read_20_pages.yml"): {
        "name": "Read 20 pages", "type": "task", "duration": "30m", "tags": ["reading"],
        "due_date": "2026-04-17",
    },
    os.path.join("tasks", "call_the_bank.yml"): {
        "name": "Call the bank", "type": "task", "duration": "15m", "tags": ["admin"],
        "due_date": "2026-04-17",
    },
    os.path.join("tasks", "reply_to_landlord.yml"): {
        "name": "Reply to landlord", "type": "task", "duration": "20m", "tags": ["admin"],
        "due_date": "2026-04-17",
    },
}


def _write(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def _run_builder_day(completions=None, day=None):
    with temporary_kairos_user_fixture() as fixture:
        user_dir = fixture["user_dir"]
        if completions:
            _write(
                os.path.join(user_dir, "schedules", "completions", f"{NOW.date().isoformat()}.yml"),
                {"entries": {
                    f"{name}@07:00": {"name": name, "status": status, "logged_at": "2026-04-16T07:30:00"}
                    for name, status in completions.items()
                }},
            )
        # Replace the fixture's hand-written day with a builder-shaped one.
        days_dir = os.path.join(user_dir, "days")
        for name in os.listdir(days_dir):
            os.remove(os.path.join(days_dir, name))
        _write(os.path.join(days_dir, "builder_day.yml"), day or BUILDER_DAY)
        for rel_path, payload in FILES.items():
            _write(os.path.join(user_dir, rel_path), payload)
        result = KairosV2Scheduler({"now": NOW}).generate_schedule(NOW.date())
    return result.get("schedule", {})


def _all_names(blocks):
    names = []
    for block in blocks:
        names.append(block.get("name"))
        names.extend(child.get("name") for child in (block.get("children") or []))
    return names


class TestDurationFormats(unittest.TestCase):
    def test_minutes_and_hour_minute_strings_are_understood(self):
        coerce = KairosV2Scheduler({})._coerce_minutes
        self.assertEqual(coerce("15m"), 15)
        self.assertEqual(coerce("90 min"), 90)
        self.assertEqual(coerce("1h30m"), 90)
        self.assertEqual(coerce("2h 15m"), 135)
        self.assertEqual(coerce("1.5h"), 90)
        self.assertEqual(coerce("45"), 45)
        self.assertEqual(coerce(20), 20)
        self.assertIsNone(coerce("soon"))
        self.assertIsNone(coerce(""))


class TestTemplateNormalization(unittest.TestCase):
    def test_builder_times_become_scheduler_times_without_overriding_explicit_ones(self):
        node = {
            "children": [
                {"name": "A", "ideal_start_time": "09:00", "ideal_end_time": "10:00"},
                {"name": "B", "start": "11:00", "end": "11:30"},
                {"name": "C", "start_time": "12:00", "ideal_start_time": "13:00",
                 "children": [{"name": "D", "ideal_start_time": "12:10"}]},
            ],
        }
        normalize_template_times(node)
        a, b, c = node["children"]
        self.assertEqual((a["start_time"], a["end_time"]), ("09:00", "10:00"))
        self.assertEqual((b["start_time"], b["end_time"]), ("11:00", "11:30"))
        self.assertEqual(c["start_time"], "12:00")
        self.assertEqual(c["children"][0]["start_time"], "12:10")

    def test_lowercase_keys_prefer_existing_lowercase_value(self):
        out = lowercase_top_level_keys({"Name": "Old", "name": "New", "Duration": 5})
        self.assertEqual(out, {"name": "New", "duration": 5})


class TestBuilderShapedDay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schedule = _run_builder_day()
        cls.blocks = cls.schedule.get("conceptual_schedule", {}).get("conceptual_blocks", [])
        cls.by_name = {block.get("name"): block for block in cls.blocks}

    def test_template_is_found_by_its_capitalised_name(self):
        self.assertEqual((self.schedule.get("day_template") or {}).get("name"), "Builder Day")

    def test_day_ends_at_the_sleep_anchor_not_the_fallback(self):
        budget = self.schedule.get("day_budget", {})
        self.assertEqual(budget.get("sleep_boundary_source"), "sleep_anchor")
        self.assertEqual(budget.get("sleep_boundary_time"), "23:30")

    def test_anchor_keeps_its_authored_time(self):
        lunch = self.by_name.get("Lunch")
        self.assertIsNotNone(lunch)
        self.assertEqual((lunch.get("start_time"), lunch.get("end_time")), ("12:30", "13:15"))

    def test_timed_child_block_is_placed_at_its_time(self):
        evening = self.by_name.get("Evening Wind Down")
        self.assertIsNotNone(evening)
        self.assertEqual(evening.get("kind"), "fixed_time")
        self.assertEqual((evening.get("start_time"), evening.get("end_time")), ("21:30", "22:00"))

    def test_tag_filtered_window_is_filled_with_matching_tasks(self):
        admin = self.by_name.get("Admin")
        self.assertIsNotNone(admin)
        self.assertEqual(admin.get("start_time"), "10:00")
        self.assertEqual(
            sorted(child.get("name") for child in admin.get("children") or []),
            ["Call the bank", "Reply to landlord"],
        )

    def test_routine_member_is_not_scheduled_a_second_time(self):
        self.assertNotIn("Read 20 pages", _all_names(self.blocks))
        covered = {
            row.get("identity"): row.get("covered_by")
            for row in self.schedule.get("day_population", {}).get("covered_by_structure", [])
        }
        self.assertEqual(covered.get("task:read 20 pages"), "member_of:routine:evening wind down")


class TestClosedBlocksStayClosed(unittest.TestCase):
    def test_skipped_item_is_not_handed_back_on_the_same_day(self):
        schedule = _run_builder_day(completions={"Call the bank": "skipped"})
        blocks = schedule.get("conceptual_schedule", {}).get("conceptual_blocks", [])
        self.assertNotIn("Call the bank", _all_names(blocks))
        self.assertIn("Reply to landlord", _all_names(blocks))
        impossible = {
            row.get("name"): row.get("impossible_reason")
            for row in schedule.get("reality_filtered_candidates", {}).get("impossible_candidates", [])
        }
        self.assertEqual(impossible.get("Call the bank"), "skipped_today")

    def test_members_of_a_routine_finished_today_are_not_rescheduled(self):
        # An untimed routine (no slot of its own) that the pilot already completed.
        day = {
            "Name": "Builder Day",
            "children": [
                {"type": "timeblock", "name": "Sleep", "duration": 480, "ideal_start_time": "23:30",
                 "ideal_end_time": "07:30", "anchored": True, "reschedule": "never"},
                {"type": "routine", "name": "Evening Wind Down"},
            ],
        }
        schedule = _run_builder_day(completions={"Evening Wind Down": "completed"}, day=day)
        blocks = schedule.get("conceptual_schedule", {}).get("conceptual_blocks", [])
        self.assertNotIn("Read 20 pages", _all_names(blocks))
        covered = {
            row.get("identity"): row.get("covered_by")
            for row in schedule.get("day_population", {}).get("covered_by_structure", [])
        }
        self.assertEqual(covered.get("task:read 20 pages"), "parent_closed_today:routine:evening wind down")

    def test_an_open_untimed_routine_is_planned_whole_with_its_steps(self):
        # Changed with decision D1 (docs/scheduling/item_lengths.md, 2026-11-18). A
        # routine without a length of its own used to be dropped, and only those of
        # its steps that were in scope by themselves (here a task with a due date)
        # were placed, one by one. Now the routine is planned as one block for the
        # total of its steps, which keeps them together, and its steps are covered
        # by it rather than lost or planned twice.
        day = {
            "Name": "Builder Day",
            "children": [
                {"type": "timeblock", "name": "Sleep", "duration": 480, "ideal_start_time": "23:30",
                 "ideal_end_time": "07:30", "anchored": True, "reschedule": "never"},
                {"type": "routine", "name": "Evening Wind Down"},
            ],
        }
        schedule = _run_builder_day(day=day)
        blocks = schedule.get("conceptual_schedule", {}).get("conceptual_blocks", [])
        self.assertIn("Evening Wind Down", _all_names(blocks))
        self.assertNotIn("Read 20 pages", _all_names(blocks))
        covered = {
            row.get("identity"): row.get("covered_by")
            for row in schedule.get("day_population", {}).get("covered_by_structure", [])
        }
        self.assertEqual(covered.get("task:read 20 pages"), "member_of:routine:evening wind down")
        lengths = {row["name"]: (row["minutes"], row["source"]) for row in schedule.get("assumed_lengths") or []}
        self.assertEqual(lengths.get("Evening Wind Down"), (30, "steps"))


if __name__ == "__main__":
    unittest.main()
