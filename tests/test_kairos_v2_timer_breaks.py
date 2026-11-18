"""Authored break blocks reach the timer as breaks (2026-11-18).

A day-template node `type: timeblock, subtype: break` with a fixed time used to
reach the timer as ordinary work: Kairos v2 dropped the subtype when it built
the block, so `start day` counted the break as focus work, asked "Did you
complete Break?" and could award points for it. The timer is documented to
treat buffer and break blocks as non-completable break phases
(docs/reference/cli_commands.md, `timer`). Found while fixing the stale timer
test in tests/test_timer_break_buffer_behavior.py.
"""

import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from modules.scheduler.runtime import build_day_runtime_payload, build_schedule_plan
from test_kairos_v2_gaps_and_breathing_room import _result, at

BREAK = {"name": "Break", "type": "timeblock", "subtype": "break",
         "start_time": "15:00", "end_time": "15:15", "duration": 15}
BUFFER = {"name": "Buffer", "type": "timeblock", "subtype": "buffer",
          "start_time": "16:00", "end_time": "16:20", "duration": 20}
SLOT = {"name": "Deep work", "type": "timeblock",
        "start_time": "17:00", "end_time": "18:00", "duration": 60}
ANCHOR = {"name": "Work", "type": "timeblock", "reschedule": "never",
          "start_time": "18:30", "end_time": "19:30", "duration": 60}

NOW = at(14, 0)


def _run(children):
    return _result(children, {}, NOW)


def _timer_blocks(children):
    """Name -> block of the plan the timer runs (`start day` builds the same one)."""
    payload = build_day_runtime_payload(NOW.date(), _run(children))
    plan = build_schedule_plan(payload, now_dt=NOW, date_key=NOW.date().isoformat())
    return {block["name"]: block for block in plan["blocks"]}


class AuthoredBreaksAreTimerBreaks(unittest.TestCase):
    def test_a_break_block_is_a_break_for_the_timer(self):
        block = _timer_blocks([BREAK])["Break"]
        self.assertTrue(block["is_buffer"])
        self.assertTrue(block["is_break"])
        self.assertEqual(block["buffer_type"], "break")

    def test_the_break_keeps_its_time(self):
        block = _timer_blocks([BREAK])["Break"]
        self.assertEqual((block["start_time"], block["end_time"]), ("15:00", "15:15"))

    def test_the_timer_unit_records_the_subtype(self):
        units = _run([BREAK])["schedule"]["timer_handoff"]["execution_units"]
        unit = next(u for u in units if u["name"] == "Break")
        self.assertEqual(unit.get("subtype"), "break")

    def test_a_buffer_block_is_still_a_break(self):
        self.assertTrue(_timer_blocks([BUFFER])["Buffer"]["is_buffer"])

    def test_ordinary_fixed_slots_and_anchors_stay_work(self):
        blocks = _timer_blocks([SLOT, ANCHOR])
        self.assertFalse(blocks["Deep work"]["is_buffer"])
        self.assertFalse(blocks["Work"]["is_buffer"])


if __name__ == "__main__":
    unittest.main()
