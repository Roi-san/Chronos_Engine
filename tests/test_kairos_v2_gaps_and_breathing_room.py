"""
Where Kairos puts flexible work in the free gaps of a day, and how tightly.

Issue 2 in docs/ISSUES_AND_NEXT_STEPS.md: at 22:05 with Gym fixed at 22:30, a
20-minute task with a deadline today went to 23:15, after the gym, although it
fitted before it. Cause: urgent work (due / deadline / goal or commitment push /
added by hand) goes into a "helper window", and helper windows were only opened
in gaps of 30+ minutes, so urgent work jumped over smaller gaps while ordinary
work took them.

Decisions (pilot, 2026-11-18), write-up in docs/scheduling/gaps_and_breathing_room.md:
- Urgent work takes the earliest gap it fits in.
- Breathing room: the 5 minutes of buffer_settings.yml (global_dynamic_buffer)
  between items, before a fixed block and after one, but only where the day
  has room. It never changes what gets planned, only where inside a gap.
- Spreading work out on light days: an open decision, nothing built.
"""
import os
import sys
import unittest
from datetime import datetime

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from chronos_fixture import temporary_kairos_user_fixture
from modules.scheduler.kairos_v2 import KairosV2Scheduler
from modules.scheduler.runtime import build_day_runtime_payload, get_flattened_runtime_items
from test_kairos_v2_direction import _seed, _write

TODAY = "2026-04-16"  # the fixture's Thursday
BREATHING_ON = {"settings/buffer_settings.yml": {"global_dynamic_buffer": {
    "buffer_duration_minutes": 5, "buffer_interval_minutes": 5}}}


def at(hour, minute=0):
    return datetime(2026, 4, 16, hour, minute)


def hm(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def mins(text):
    hours, minutes = text.split(":")
    return int(hours) * 60 + int(minutes)


SLEEP = {"name": "Sleep", "type": "timeblock", "sleep": True, "reschedule": "never",
         "start_time": "23:55", "duration": 480}


def gym(start="22:30", minutes=45):
    return {"name": "Gym", "type": "habit", "start_time": start, "duration": minutes}


def anchor(name, start, end):
    return {"name": name, "type": "timeblock", "start_time": start, "end_time": end,
            "duration": mins(end) - mins(start), "reschedule": "never"}


def task(name, minutes, **extra):
    return {"name": name, "type": "task", "duration": f"{minutes}m", **extra}


def habit(name, minutes, **extra):
    return {"name": name, "type": "habit", "duration": f"{minutes}m", "frequency": "daily", **extra}


def _result(children, files, now, settings=None):
    with temporary_kairos_user_fixture() as fixture:
        user_dir = fixture["user_dir"]
        days_dir = os.path.join(user_dir, "days")
        for name in os.listdir(days_dir):
            os.remove(os.path.join(days_dir, name))
        # The base fixture's daily "Stretch Break" would join every plan; keep plans exact.
        os.remove(os.path.join(user_dir, "habits", "stretch_break.yml"))
        _write(os.path.join(days_dir, "day.yml"), {"name": "Day", "type": "day", "children": [SLEEP, *children]})
        _seed(user_dir, {**(settings or {}), **files})
        return KairosV2Scheduler({"now": now, "start_from_now": True}).generate_schedule(now.date())


def _plan(children, files, now, settings=None):
    return _result(children, files, now, settings).get("schedule", {})


def _items(schedule):
    """(name, start, end) of every placed flexible item, by start."""
    rows = []
    for block in schedule.get("conceptual_schedule", {}).get("conceptual_blocks", []):
        for child in block.get("children") or []:
            rows.append((child["name"], child["start_time"], child["end_time"]))
    return sorted(rows, key=lambda row: mins(row[1]))


def _where(schedule, name):
    for row in _items(schedule):
        if row[0] == name:
            return row[1], row[2]
    return None


TAXES_DEADLINE = {"tasks/taxes.yml": task("File taxes", 20, deadline=TODAY)}
LIGHT_DAY = ([anchor("Lunch", "13:00", "13:30")],
             {"habits/a.yml": habit("Read", 30), "habits/b.yml": habit("Walk", 30), "habits/c.yml": habit("Journal", 15)},
             at(11, 0))


class UrgentWorkTakesTheEarliestGap(unittest.TestCase):
    """Breathing room off (the fixture has no global_dynamic_buffer), to test this on its own."""

    def test_a_deadline_task_goes_before_the_fixed_slot(self):
        schedule = _plan([gym()], TAXES_DEADLINE, at(22, 5))
        self.assertEqual(_where(schedule, "File taxes"), ("22:05", "22:25"))

    def test_a_task_due_today_goes_before_the_fixed_slot(self):
        schedule = _plan([gym()], {"tasks/taxes.yml": task("File taxes", 20, due_date=TODAY)}, at(22, 5))
        self.assertEqual(_where(schedule, "File taxes"), ("22:05", "22:25"))

    def test_a_report_due_today_takes_the_gap_before_a_meeting(self):
        schedule = _plan([anchor("Meeting", "09:00", "12:30"), anchor("Lunch", "12:30", "13:30")],
                         {"tasks/report.yml": task("Send report", 20, due_date=TODAY)}, at(8, 35))
        self.assertEqual(_where(schedule, "Send report"), ("08:35", "08:55"))

    def test_urgent_work_gets_the_early_gap_before_ordinary_work(self):
        schedule = _plan([gym()], {**TAXES_DEADLINE, "habits/tidy.yml": habit("Tidy desk", 20)}, at(22, 5))
        self.assertEqual(_where(schedule, "File taxes"), ("22:05", "22:25"))
        self.assertEqual(_where(schedule, "Tidy desk"), ("23:15", "23:35"))

    def test_urgent_work_that_does_not_fit_still_goes_to_a_later_gap(self):
        schedule = _plan([gym()], {"tasks/taxes.yml": task("File taxes", 30, deadline=TODAY)}, at(22, 5))
        self.assertEqual(_where(schedule, "File taxes"), ("23:15", "23:45"))

    def test_an_explicit_minimum_gap_setting_is_still_honoured(self):
        settings = {"settings/scheduling_settings.yml": {"runtime_helper_windows": {"minimum_gap_minutes": 30}}}
        schedule = _plan([gym()], TAXES_DEADLINE, at(22, 5), settings)
        self.assertEqual(_where(schedule, "File taxes"), ("23:15", "23:35"))


class BreathingRoom(unittest.TestCase):
    """buffer_settings.yml global_dynamic_buffer: 5 minutes, after every 5+ minutes of work."""

    def test_five_minutes_between_items(self):
        schedule = _plan(*LIGHT_DAY, BREATHING_ON)
        self.assertEqual(_items(schedule), [
            ("Journal", "11:00", "11:15"), ("Read", "11:20", "11:50"), ("Walk", "11:55", "12:25")])

    def test_five_minutes_before_a_fixed_slot(self):
        schedule = _plan([gym()], {"habits/a.yml": habit("Stretch", 10), "habits/b.yml": habit("Tidy desk", 10)},
                         at(22, 0), BREATHING_ON)
        self.assertEqual(_items(schedule), [("Stretch", "22:00", "22:10"), ("Tidy desk", "22:15", "22:25")])

    def test_five_minutes_after_a_fixed_block(self):
        schedule = _plan([anchor("Work", "14:00", "15:00")], {"habits/a.yml": habit("Walk", 20)},
                         at(14, 30), BREATHING_ON)
        self.assertEqual(_where(schedule, "Walk"), ("15:05", "15:25"))

    def test_the_first_item_starts_now_without_a_margin(self):
        schedule = _plan(*LIGHT_DAY, BREATHING_ON)
        self.assertEqual(_items(schedule)[0][1], "11:00")

    def test_a_task_that_only_fits_without_breathing_room_is_still_placed(self):
        schedule = _plan([gym()], {"tasks/taxes.yml": task("File taxes", 25, deadline=TODAY)},
                         at(22, 5), BREATHING_ON)
        self.assertEqual(_where(schedule, "File taxes"), ("22:05", "22:30"))

    def test_when_room_is_short_the_margin_before_a_fixed_slot_comes_first(self):
        # 24 minutes of work in a 30-minute gap: room for one margin, not two.
        schedule = _plan([gym()], {"habits/a.yml": habit("Stretch", 12), "habits/b.yml": habit("Tidy desk", 12)},
                         at(22, 0), BREATHING_ON)
        self.assertEqual(_items(schedule), [("Stretch", "22:00", "22:12"), ("Tidy desk", "22:12", "22:24")])

    def test_breathing_room_never_changes_what_gets_planned(self):
        cases = [
            ([gym()], {**TAXES_DEADLINE, "habits/tidy.yml": habit("Tidy desk", 20), "habits/s.yml": habit("Stretch", 10)}, at(22, 5)),
            LIGHT_DAY,
            ([anchor("Meeting", "09:00", "12:30")],
             {"tasks/r.yml": task("Send report", 20, due_date=TODAY), "habits/j.yml": habit("Journal", 15),
              "habits/w.yml": habit("Walk", 30)}, at(8, 20)),
        ]
        for children, files, now in cases:
            with self.subTest(now=now):
                off = {row[0] for row in _items(_plan(children, files, now))}
                on = {row[0] for row in _items(_plan(children, files, now, BREATHING_ON))}
                self.assertEqual(on, off)

    def test_items_in_a_window_get_breathing_room_and_stay_inside_it(self):
        window = {"name": "Admin", "type": "window", "window": True, "start_time": "10:00", "end_time": "11:00",
                  "duration": 60, "filters": {"tags": ["admin"]}}
        files = {"tasks/a.yml": task("Pay bill", 20, due_date=TODAY, tags=["admin"]),
                 "tasks/b.yml": task("Reply to landlord", 20, due_date=TODAY, tags=["admin"])}
        rows = [row for row in _items(_plan([window], files, at(9, 0), BREATHING_ON)) if row[0] in ("Pay bill", "Reply to landlord")]
        self.assertEqual(len(rows), 2)
        self.assertEqual(mins(rows[1][1]) - mins(rows[0][2]), 5)
        for _, start, end in rows:
            self.assertGreaterEqual(mins(start), mins("10:00"))
            self.assertLessEqual(mins(end), mins("11:00"))

    def test_custom_minutes_and_interval(self):
        # 10-minute breathers, but only after 45+ minutes of continuous work.
        settings = {"settings/buffer_settings.yml": {"global_dynamic_buffer": {
            "buffer_duration_minutes": 10, "buffer_interval_minutes": 45}}}
        schedule = _plan(*LIGHT_DAY, settings)
        self.assertEqual(_items(schedule), [
            ("Journal", "11:00", "11:15"), ("Read", "11:15", "11:45"), ("Walk", "11:55", "12:25")])

    def test_off_without_the_setting(self):
        schedule = _plan(*LIGHT_DAY)
        self.assertEqual(_items(schedule), [
            ("Journal", "11:00", "11:15"), ("Read", "11:15", "11:45"), ("Walk", "11:45", "12:15")])

    def test_the_gap_fill_block_spans_its_spaced_items(self):
        blocks = _plan(*LIGHT_DAY, BREATHING_ON)["conceptual_schedule"]["conceptual_blocks"]
        fill = [block for block in blocks if block.get("kind") == "gap_fill"]
        self.assertEqual(len(fill), 1)
        self.assertEqual((fill[0]["start_time"], fill[0]["end_time"]), ("11:00", "12:25"))
        self.assertEqual(fill[0]["name"], "Gap Fill 11:00-12:25")

    def test_the_timer_and_the_schedule_file_get_the_spaced_times(self):
        result = _result(*LIGHT_DAY, BREATHING_ON)
        units = [u for u in result["schedule"]["timer_handoff"]["execution_units"] if u["name"] != "Lunch"]
        self.assertEqual([(u["name"], u["start_time"], u["end_time"]) for u in units],
                         [("Journal", "11:00", "11:15"), ("Read", "11:20", "11:50"), ("Walk", "11:55", "12:25")])
        items = get_flattened_runtime_items(build_day_runtime_payload(at(11, 0).date(), result))
        walk = next(item for item in items if item.get("name") == "Walk")
        self.assertEqual((walk["start_time"], walk["end_time"]), ("11:55", "12:25"))

    def test_the_schedule_records_what_breathing_room_did(self):
        record = _plan(*LIGHT_DAY, BREATHING_ON)["breathing_room"]
        self.assertEqual((record["minutes"], record["interval_minutes"]), (5, 5))
        self.assertEqual(record["margins_added"], 2)
        self.assertEqual(record["items_moved"], 2)


if __name__ == "__main__":
    unittest.main()
