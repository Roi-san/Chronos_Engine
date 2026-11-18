"""
What Home says about recurring items (roadmap step 1c, decision D2).

Home (`utilities/dashboard/home_api.py`) only turns what Kairos's direction
module says into the reasons and tags a block shows. The wording is built in
`modules/scheduler/recurrence.py`; here we check that it arrives, that a
commitment's state wins over a recurring one, and the "kept although" sentence.
"""
import os
import sys
import unittest
from datetime import date
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from modules.scheduler import direction as Direction  # noqa: E402
from utilities.dashboard import home_api as HomeApi  # noqa: E402

LAST_CHANCE = "Once a week: missed its day (Saturday), last chance this week."


def _loaded(signal):
    return {"by_identity": {"habit:laundry": signal}, "commitments": [], "goals": []}


def _direction(loaded):
    with mock.patch.object(Direction, "load_direction", return_value=loaded):
        return HomeApi._direction({"scaled_down": []})


class RecurringReasonsOnHome(unittest.TestCase):
    def test_a_recurring_reason_and_its_state_reach_the_block(self):
        out = _direction(_loaded({"recurring": {"state": "last_chance", "level": 1.0, "reason": LAST_CHANCE}}))
        self.assertEqual(out["by_name"]["laundry"], {"reasons": [LAST_CHANCE], "state": "last_chance"})

    def test_a_commitments_state_wins_over_a_recurring_one(self):
        out = _direction(_loaded({
            "commitment": {"state": "at_risk", "level": 0.7, "reason": "Counts toward \"Clean flat\" (1 of 2 done)"},
            "recurring": {"state": "last_chance", "level": 1.0, "reason": LAST_CHANCE},
        }))
        self.assertEqual(out["by_name"]["laundry"]["state"], "at_risk")
        self.assertEqual(out["by_name"]["laundry"]["reasons"], ["Counts toward \"Clean flat\" (1 of 2 done)", LAST_CHANCE])

    def test_home_asks_the_shared_helper_what_day_it_is(self):
        with mock.patch.object(Direction, "load_direction", return_value=_loaded({})) as load, \
                mock.patch("modules.scheduler.periods.today", return_value=date(2026, 4, 16)):
            HomeApi._direction({})
        self.assertEqual(load.call_args[0][1], date(2026, 4, 16))


class KeptSentence(unittest.TestCase):
    def test_recurring_importance_is_named(self):
        effects = HomeApi.status_effects({"kept": [{
            "name": "Clean Garage", "kind": "important",
            "importance_sources": [{"source": "recurring", "value": 1.0}],
            "short_dimensions": [{"dimension": "energy", "today": "low", "accepts": ["high"]}],
        }]})
        self.assertEqual(effects["kept"]["clean garage"],
                         "Kept although energy is low (needs high): keeping its rhythm matters more than the strain.")


if __name__ == "__main__":
    unittest.main()
