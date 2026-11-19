"""
Which day template Kairos uses today, and saying why (decision D6, 2026-11-19;
issues 16 and 40; `docs/scheduling/planning_and_tracking_model.md`, proposal B).

Kairos picks the template itself on every plan: templates allowed on today's
weekday, then the Today widget's preferences, then the one closest to how you
said you feel (status), then, new, a template set for today's weekday before a
general one, then the first by name. The pilot (2026-11-19) does not need to pick
a template in the dashboard for now; a picker may come later (D6: your pick wins
for the day, and status still lightens single items).

Before:
- #40: "Weekend" (days: saturday, sunday) lost to "Normal Day" (no days) on
  Saturday, because both fit and "N" comes before "W".
- `days: []`, documented as "any day", matched no day.
- Nobody could see why a template was chosen (Home did not say which).

Fixture clock: Thursday 16 April 2026, 08:00 (Saturday is 18 April).
"""
import io
import os
import shutil
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from chronos_fixture import temporary_kairos_user_fixture  # noqa: E402
from modules.scheduler.kairos_v2 import KairosV2Scheduler  # noqa: E402
from test_kairos_v2_direction import _write  # noqa: E402
from utilities.dashboard import home_api  # noqa: E402

THURSDAY = datetime(2026, 4, 16, 8, 0)
SATURDAY = datetime(2026, 4, 18, 8, 0)
SLEEP = {"name": "Core Sleep", "type": "timeblock", "start_time": "23:30", "end_time": "07:30",
         "duration": 480, "reschedule": "never", "category": "sleep"}
OK_DAY = {"health": "good", "energy": "medium"}
SICK_DAY = {"health": "poor", "energy": "low"}      # what Home's Sick day button sets


def template(name, **extra):
    return {"name": name, "type": "day", "children": [SLEEP], **extra}


NORMAL = template("Normal Day")
WEEKEND = template("Weekend", days=["saturday", "sunday"])
SICK = template("Sick Day", status_requirements={"health": "poor", "energy": "low"})


def choose(templates, now=THURSDAY, status=OK_DAY, context=None):
    with temporary_kairos_user_fixture() as fixture:
        user = fixture["user_dir"]
        for name in os.listdir(os.path.join(user, "days")):
            os.remove(os.path.join(user, "days", name))
        # The fixture knows only energy and focus, without their scales; status can
        # only be compared with the shipped dimensions and values (read, not changed).
        for settings_file in ("status_settings.yml", "health_settings.yml", "energy_settings.yml"):
            shutil.copy(os.path.join(ROOT_DIR, "user", "settings", settings_file), os.path.join(user, "settings", settings_file))
        for tpl in templates:
            _write(os.path.join(user, "days", tpl["name"].lower().replace(" ", "_") + ".yml"), tpl)
        _write(os.path.join(user, "profile", "current_status.yml"), status)
        with redirect_stdout(io.StringIO()):
            result = KairosV2Scheduler({"now": now, **(context or {})}).generate_schedule(now.date())
    schedule = result.get("schedule", {})
    return (schedule.get("day_template") or {}).get("name"), schedule.get("day_template_choice") or {}


class WhichTemplate(unittest.TestCase):
    def test_a_weekend_template_wins_on_saturday(self):
        name, choice = choose([NORMAL, WEEKEND], now=SATURDAY)
        self.assertEqual(name, "Weekend")
        self.assertEqual(choice["reason"], "weekday")
        self.assertIn("Saturday", choice["why"])

    def test_and_the_normal_day_on_thursday(self):
        name, choice = choose([NORMAL, WEEKEND])
        self.assertEqual(name, "Normal Day")
        self.assertEqual(choice["reason"], "only")

    def test_feeling_ill_still_beats_the_weekday(self):
        name, choice = choose([NORMAL, WEEKEND, SICK], now=SATURDAY, status=SICK_DAY)
        self.assertEqual(name, "Sick Day")
        self.assertEqual(choice["reason"], "status")
        self.assertIn("health poor", choice["why"])

    def test_a_tie_says_the_first_by_name_was_taken(self):
        name, choice = choose([template("Workday"), template("Chill Day")])
        self.assertEqual(name, "Chill Day")
        self.assertEqual(choice["reason"], "name")
        self.assertIn("first by name", choice["why"])

    def test_empty_days_means_any_day(self):
        name, _ = choose([template("Any Day", days=[])])
        self.assertEqual(name, "Any Day")

    def test_a_forced_template(self):
        name, choice = choose([NORMAL, SICK], context={"force_template": "Sick Day"})
        self.assertEqual(name, "Sick Day")
        self.assertEqual(choice["reason"], "chosen")

    def test_no_template_for_today(self):
        name, choice = choose([WEEKEND])
        self.assertIsNone(name)
        self.assertEqual(choice["reason"], "none")
        self.assertIn("Thursday", choice["why"])


class WhatHomeSays(unittest.TestCase):
    def test_the_template_line(self):
        meta = {"day_template_choice": {"name": "Weekend", "reason": "weekday", "why": "it is set for Saturdays"}}
        self.assertEqual(home_api.day_template_line(meta), {"name": "Weekend", "why": "it is set for Saturdays"})
        self.assertIsNone(home_api.day_template_line({}))

    def test_plan_notes_name_what_would_otherwise_be_silent(self):
        meta = {
            "sleep_blocks": {"names": ["Sleep"], "by_name": True, "note": "No block on 'My Day' is marked as sleep, ..."},
            "unreadable_files": [{"file": "habits/broken.yml", "error": "line 2, column 12: ..."}],
        }
        notes = home_api.plan_notes(meta)
        self.assertEqual(len(notes), 2)
        self.assertTrue(notes[0].startswith("No block on 'My Day'"))
        self.assertIn("habits/broken.yml", notes[1])
        self.assertEqual(home_api.plan_notes({"sleep_blocks": {"by_name": False}, "unreadable_files": []}), [])


if __name__ == "__main__":
    unittest.main()
