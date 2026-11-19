"""
Start day waits for a fixed block that is still ahead (Lunch at 10:00 when it
is 08:30) instead of starting it now (`modules/timer/main._is_future_anchor_block`).

Issue 21 (fixed 2026-11-19): these tests used the real clock and built "90
minutes from now" as a clock time, which wrapped past midnight between 22:30 and
midnight ("00:05" is not after "22:35"), so two of them failed every evening.
The clock is now fixed at 08:30.
"""
import os
import sys
import unittest
from datetime import datetime
from unittest.mock import patch

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from modules.timer import main as Timer  # noqa: E402


class _FixedClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 11, 19, 8, 30)


AHEAD = "10:00"
PAST = "07:00"


class TestTimerAnchorWait(unittest.TestCase):
    def setUp(self):
        clock = patch.object(Timer, "datetime", _FixedClock)
        clock.start()
        self.addCleanup(clock.stop)

    def test_future_anchor_detected_by_reschedule(self):
        block = {"name": "Lunch", "schedule_type": "task", "reschedule": "never", "start": AHEAD}
        self.assertTrue(Timer._is_future_anchor_block(block))

    def test_future_anchor_detected_by_window_name(self):
        block = {"name": "Dinner", "schedule_type": "task", "window_name": "ANCHOR", "start": AHEAD}
        self.assertTrue(Timer._is_future_anchor_block(block))

    def test_non_anchor_not_waiting(self):
        block = {"name": "Study", "schedule_type": "task", "reschedule": "auto", "start": AHEAD}
        self.assertFalse(Timer._is_future_anchor_block(block))

    def test_anchor_already_started_is_not_waited_for(self):
        # Added 2026-11-19: the other side of the same rule.
        block = {"name": "Breakfast", "schedule_type": "task", "reschedule": "never", "start": PAST}
        self.assertFalse(Timer._is_future_anchor_block(block))


if __name__ == "__main__":
    unittest.main()
