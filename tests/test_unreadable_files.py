"""
One file Kairos cannot read must not stop the whole plan (issue 31, 2026-11-19).

Before: a single item, day template or status file with a YAML mistake (a hand
edit, an AI writing a file) made `modules/scheduler/v1.read_template` raise, and
the whole plan failed: "[Kairos] Active scheduling failed: mapping values are not
allowed here", no plan at all, and the command still exited normally. Now the
file is skipped, the rest of the day is planned, and the skipped files are
listed in `schedule.unreadable_files`, the decision log and the console.

Fixture clock: Thursday 16 April 2026, 08:00.
"""
import io
import os
import sys
import unittest
from contextlib import ExitStack, redirect_stdout
from datetime import datetime
from unittest.mock import patch

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from chronos_fixture import temporary_kairos_user_fixture  # noqa: E402
from modules.scheduler import v1 as SchedulerV1  # noqa: E402
from modules.scheduler.kairos_v2 import KairosV2Scheduler  # noqa: E402
from test_kairos_v2_direction import PLAIN_DAY, _placed, _seed, _write  # noqa: E402

NOW = datetime(2026, 4, 16, 8, 0)
BROKEN = "name: Broken habit\n  frequency: [daily\nduration: 10\n"   # bad indentation, unclosed list
READ = {"habits/read.yml": {"name": "Read", "type": "habit", "duration": "30m", "frequency": "daily"}}


def _install(user_dir, files, raw):
    days_dir = os.path.join(user_dir, "days")
    for name in os.listdir(days_dir):
        os.remove(os.path.join(days_dir, name))
    _write(os.path.join(days_dir, "plain_day.yml"), PLAIN_DAY)
    _seed(user_dir, files)
    for rel, content in (raw or {}).items():
        path = os.path.join(user_dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(content if isinstance(content, bytes) else content.encode("utf-8"))


def _plan(files=None, raw=None):
    with temporary_kairos_user_fixture() as fixture:
        _install(fixture["user_dir"], files or READ, raw)
        with redirect_stdout(io.StringIO()) as out:
            result = KairosV2Scheduler({"now": NOW}).generate_schedule(NOW.date())
    return result.get("schedule", {}), out.getvalue()


class OneBadFileDoesNotStopThePlan(unittest.TestCase):
    def test_a_broken_habit_file(self):
        schedule, console = _plan(raw={"habits/broken.yml": BROKEN})
        self.assertIn("Read", _placed(schedule))
        rows = schedule["unreadable_files"]
        self.assertEqual([row["file"] for row in rows], ["habits/broken.yml"])
        self.assertIn("line 2", rows[0]["error"])
        self.assertIn("habits/broken.yml", console)          # said in the console too

    def test_a_broken_day_template_beside_a_good_one(self):
        schedule, _ = _plan(raw={"days/broken_day.yml": BROKEN})
        self.assertEqual(schedule["day_template"]["name"], "Plain Day")
        self.assertIn("Read", _placed(schedule))
        self.assertIn("days/broken_day.yml", [row["file"] for row in schedule["unreadable_files"]])

    def test_a_broken_status_file(self):
        schedule, _ = _plan(raw={"profile/current_status.yml": "energy: [high\n"})
        self.assertIn("Read", _placed(schedule))

    def test_a_file_that_is_not_text(self):
        schedule, _ = _plan(raw={"habits/binary.yml": b"name: \x98\xff\x00\n  : ["})
        self.assertIn("Read", _placed(schedule))
        self.assertIn("habits/binary.yml", [row["file"] for row in schedule["unreadable_files"]])

    def test_a_clean_run_lists_nothing_even_after_a_bad_one(self):
        _plan(raw={"habits/broken.yml": BROKEN})
        schedule, console = _plan()
        self.assertEqual(schedule["unreadable_files"], [])
        self.assertNotIn("could not read", console)


class ReadTemplate(unittest.TestCase):
    def test_good_broken_and_missing_files(self):
        with temporary_kairos_user_fixture() as fixture:
            _install(fixture["user_dir"], READ, {"habits/broken.yml": BROKEN})
            SchedulerV1.UNREADABLE_FILES.clear()
            good = SchedulerV1.read_template(os.path.join(fixture["user_dir"], "habits", "read.yml"))
            broken = SchedulerV1.read_template(os.path.join(fixture["user_dir"], "habits", "broken.yml"))
            missing = SchedulerV1.read_template(os.path.join(fixture["user_dir"], "habits", "nope.yml"))
            recorded = list(SchedulerV1.UNREADABLE_FILES)
        self.assertEqual(good["name"], "Read")
        self.assertIsNone(broken)
        self.assertIsNone(missing)
        self.assertEqual(len(recorded), 1)                    # a missing file is not an error


class TheRealCommand(unittest.TestCase):
    def test_today_reschedule_still_writes_a_plan(self):
        from commands import today as Today
        from modules.scheduler import load_day_runtime, schedule_path_for_date
        from modules.scheduler.runtime import get_flattened_runtime_items

        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(NOW.year, NOW.month, NOW.day, NOW.hour, NOW.minute)

        def scheduler(user_context=None):
            return KairosV2Scheduler({**(user_context or {}), "now": NOW})

        with ExitStack() as stack:
            fixture = stack.enter_context(temporary_kairos_user_fixture())
            _install(fixture["user_dir"], READ, {"habits/broken.yml": BROKEN})
            stack.enter_context(patch("modules.scheduler.KairosV2Scheduler", side_effect=scheduler))
            stack.enter_context(patch("commands.today.datetime", Clock))
            stack.enter_context(patch("commands.today.build_sleep_interrupt", return_value=None))
            with redirect_stdout(io.StringIO()):
                Today.run(["reschedule"], {})
            date_str = NOW.strftime("%Y-%m-%d")
            payload = load_day_runtime(date_str, path=schedule_path_for_date(date_str))
        names = {item.get("name") for item in get_flattened_runtime_items(payload)}
        self.assertIn("Read", names)
        self.assertEqual([row["file"] for row in payload["schedule"]["unreadable_files"]], ["habits/broken.yml"])


if __name__ == "__main__":
    unittest.main()
