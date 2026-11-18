"""Home says when Kairos assumed a length (decision D1, issue 12, 2026-11-18).

Kairos records `schedule.assumed_lengths`; `home_api.length_notes` turns it into
one sentence per block, and lists the blocks planned with the default length so
Home can tag them. The last test runs a real Kairos plan through it, so a change
to the record's shape breaks it.
"""

import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for path in (ROOT_DIR, os.path.join(ROOT_DIR, "tests"), os.path.join(ROOT_DIR, "utilities", "dashboard")):
    if path not in sys.path:
        sys.path.insert(0, path)

import home_api  # noqa: E402
from test_kairos_v2_item_lengths import MORNING_STEPS, _plan, _routine, _task  # noqa: E402

EMPTY = {"notes": {}, "unset": []}


class LengthNotes(unittest.TestCase):
    def test_nothing_recorded_gives_nothing(self):
        for record in (None, [], {}, "x", [None, 3, {"name": ""}]):
            self.assertEqual(home_api.length_notes(record), EMPTY)

    def test_a_default_length_says_so_and_is_listed(self):
        notes = home_api.length_notes([{"name": "Call the bank", "minutes": 30, "source": "default"}])
        self.assertEqual(notes["notes"]["call the bank"],
                         "No length set, so Chronos planned 30 min. Set its real length in Manage.")
        self.assertEqual(notes["unset"], ["call the bank"])

    def test_a_length_from_steps_says_so_and_is_not_listed(self):
        notes = home_api.length_notes([{"name": "Morning Routine", "minutes": 30, "source": "steps"}])
        self.assertEqual(notes["notes"]["morning routine"], "Planned for 30 min, the total of its steps.")
        self.assertEqual(notes["unset"], [])

    def test_a_real_plan(self):
        schedule = _plan([_routine("Morning Routine", MORNING_STEPS)], {"tasks/bank.yml": _task("Call the bank")})
        notes = home_api.length_notes(schedule.get("assumed_lengths"))
        self.assertIn("call the bank", notes["unset"])
        self.assertIn("morning routine", notes["notes"])


if __name__ == "__main__":
    unittest.main()
