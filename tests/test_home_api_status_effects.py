"""
Home's reading of what today's status did to the plan (step 3 of
docs/scheduling/status_scale_down_design.md).

`utilities/dashboard/home_api.status_effects` turns Kairos's
`schedule.status_scale_down` record into the "Saved for a better day" list
(with the type Add back needs) and the "Kept although ..." notes.
The last class runs real Kairos plans through it, so a change to the record's
shape on the scheduler side breaks these tests instead of silently blanking Home.
"""
import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
DASH_DIR = os.path.join(ROOT_DIR, "utilities", "dashboard")
for path in (ROOT_DIR, TESTS_DIR, DASH_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

import home_api  # noqa: E402
from test_kairos_v2_status_scale_down import EXHAUSTED, LOW, MEDIUM, _plan, needs  # noqa: E402

ENERGY_LOW = {"dimension": "energy", "today": "low", "accepts": ["high", "medium"], "steps_short": 1}


class SavedList(unittest.TestCase):
    def test_nothing_recorded_gives_empty_lists(self):
        for record in (None, {}, "garbage", {"saved": "x", "kept": 3}):
            self.assertEqual(home_api.status_effects(record), {"saved": [], "kept": {}})

    def test_a_saved_item_carries_its_type_for_add_back(self):
        record = {"saved": [{"name": "Gym", "identity": "habit:gym", "kind": "saved", "short_dimensions": [ENERGY_LOW]}]}
        [row] = home_api.status_effects(record)["saved"]
        self.assertEqual(row["name"], "Gym")
        self.assertEqual(row["type"], "habit")
        self.assertEqual(row["fixed_slot"], "")
        self.assertEqual(row["text"], "Today energy is low (needs high or medium).")

    def test_a_saved_fixed_slot_keeps_its_time(self):
        record = {"saved": [{"name": "Gym", "identity": "habit:gym", "fixed_slot": "18:00-19:00"}]}
        self.assertEqual(home_api.status_effects(record)["saved"][0]["fixed_slot"], "18:00-19:00")

    def test_several_short_dimensions_are_joined(self):
        health = {"dimension": "health", "today": "poor", "accepts": ["good"]}
        record = {"saved": [{"name": "Run", "identity": "habit:run", "short_dimensions": [ENERGY_LOW, health]}]}
        self.assertEqual(home_api.status_effects(record)["saved"][0]["text"],
                         "Today energy is low (needs high or medium) and health is poor (needs good).")

    def test_a_missing_type_falls_back_to_task(self):
        # `today inject` defaults to task too.
        record = {"saved": [{"name": "Write report"}]}
        self.assertEqual(home_api.status_effects(record)["saved"][0]["type"], "task")
        self.assertEqual(home_api.status_effects(record)["saved"][0]["text"], "Today does not fit it.")

    def test_an_item_recorded_twice_is_listed_once(self):
        # A fixed slot is also a flexible candidate; Kairos merges, Home dedups anyway.
        record = {"saved": [{"name": "Gym", "identity": "habit:gym"}, {"name": "gym", "identity": "habit:gym"}]}
        self.assertEqual(len(home_api.status_effects(record)["saved"]), 1)

    def test_rows_without_a_name_are_ignored(self):
        record = {"saved": [{"identity": "habit:gym"}, "x", None], "kept": [{"kind": "urgent"}]}
        self.assertEqual(home_api.status_effects(record), {"saved": [], "kept": {}})


class KeptNotes(unittest.TestCase):
    def _note(self, **row):
        record = {"kept": [{"name": "Gym", "identity": "habit:gym", "short_dimensions": [ENERGY_LOW], **row}]}
        return home_api.status_effects(record)["kept"]["gym"]

    def test_within_grace(self):
        self.assertEqual(self._note(kind="within_grace"),
                         "Kept although energy is low (needs high or medium): it is only a little short.")

    def test_urgent_reasons(self):
        self.assertTrue(self._note(kind="urgent", urgent_because="deadline_today").endswith(": its deadline is today."))
        self.assertTrue(self._note(kind="urgent", urgent_because="due_date_overdue").endswith(": it is overdue."))
        self.assertTrue(self._note(kind="urgent", urgent_because="commitment_last_chance")
                        .endswith(": it is the last chance to keep its commitment."))
        self.assertTrue(self._note(kind="urgent", urgent_because="something_new").endswith(": it is urgent."))

    def test_important_names_the_strongest_source(self):
        note = self._note(kind="important", importance_sources=[
            {"source": "priority", "value": 0.4}, {"source": "goal", "value": 0.9}])
        self.assertTrue(note.endswith(": its goal matters more than the strain."), note)

    def test_unknown_kind_still_says_kept(self):
        self.assertEqual(self._note(kind="new_kind"), "Kept although energy is low (needs high or medium).")

    def test_keyed_by_lowercase_name(self):
        record = {"kept": [{"name": "Deep Work", "kind": "within_grace"}]}
        self.assertIn("deep work", home_api.status_effects(record)["kept"])


class ThroughRealKairosPlans(unittest.TestCase):
    """The record Kairos actually writes, read by Home."""

    def test_saved_item(self):
        files = {"habits/gym.yml": {"name": "Gym", "type": "habit", "duration": "60m", "frequency": "daily",
                                    **needs(energy="high")}}
        effects = home_api.status_effects(_plan(files, status=EXHAUSTED)["status_scale_down"])
        [row] = effects["saved"]
        self.assertEqual((row["name"], row["type"]), ("Gym", "habit"))
        self.assertIn("energy is exhausted", row["text"])
        self.assertIn("needs high", row["text"])

    def test_kept_item_within_grace(self):
        files = {"habits/gym.yml": {"name": "Gym", "type": "habit", "duration": "60m", "frequency": "daily",
                                    **needs(energy="high")}}
        effects = home_api.status_effects(_plan(files, status=MEDIUM)["status_scale_down"])
        self.assertEqual(effects["saved"], [])
        self.assertIn("only a little short", effects["kept"]["gym"])

    def test_kept_item_urgent(self):
        files = {"tasks/taxes.yml": {"name": "File taxes", "type": "task", "duration": "60m",
                                     "deadline": "2026-04-16", **needs(energy="high")}}
        effects = home_api.status_effects(_plan(files, status=EXHAUSTED)["status_scale_down"])
        self.assertIn("deadline is today", effects["kept"]["file taxes"])

    def test_saved_fixed_slot(self):
        from test_kairos_v2_status_fixed_slots import SLOT, _day, gym_item

        schedule = _plan(gym_item(**needs(energy="high")), status=LOW, day=_day(SLOT))
        [row] = home_api.status_effects(schedule["status_scale_down"])["saved"]
        self.assertEqual((row["name"], row["type"], row["fixed_slot"]), ("Gym", "habit", "18:00-19:00"))


if __name__ == "__main__":
    unittest.main()
