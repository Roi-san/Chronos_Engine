"""
New items that can be planned record the day they were made (`created`),
roadmap step 1c, design decision 9 in docs/scheduling/recurrence_design.md.

A weekly to yearly item added after its turn this period starts with its next
turn instead of counting as missed; `created` is how Kairos knows. Every way of
making an item goes through `item_manager.generic_handle_new` (the console's
`new`, the dashboard's POST /api/item, wizards, an AI), so it is stamped there.
"""
import os
import sys
import unittest
from contextlib import redirect_stdout
from datetime import date
from io import StringIO

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
for path in (ROOT_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from chronos_fixture import temporary_kairos_user_fixture  # noqa: E402
from modules import item_manager as ItemManager  # noqa: E402


def _new(item_type, name, properties):
    with redirect_stdout(StringIO()):
        ItemManager.generic_handle_new(item_type, name, properties)
    return ItemManager.read_item_data(item_type, name)


class CreatedStamp(unittest.TestCase):
    def test_a_new_habit_records_today(self):
        with temporary_kairos_user_fixture():
            data = _new("habit", "Laundry", {"frequency": "weekly"})
        self.assertEqual(str(data.get("created")), date.today().isoformat())

    def test_every_schedulable_type_is_stamped(self):
        with temporary_kairos_user_fixture():
            stamped = {t: _new(t, f"Thing {t}", {}).get("created") for t in
                       ("habit", "task", "routine", "subroutine", "microroutine", "timeblock")}
        self.assertTrue(all(stamped.values()), stamped)

    def test_a_given_date_is_kept(self):
        with temporary_kairos_user_fixture():
            data = _new("habit", "Old chore", {"created": "2026-01-05"})
        self.assertEqual(str(data.get("created")), "2026-01-05")

    def test_other_types_are_left_alone(self):
        with temporary_kairos_user_fixture():
            data = _new("note", "An idea", {})
        self.assertNotIn("created", data)


if __name__ == "__main__":
    unittest.main()
