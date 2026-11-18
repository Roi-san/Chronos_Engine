"""The skills registry lists real skills only (issue 5, 2026-11-18).

`docs/agents/skills/template/skill.md` is the blank skeleton for writing a new
skill (its heading is `<Skill Name>`; skills_index.md says it is not a skill to
load). `skills list` showed it as a skill. `docs/agents/skills/templates/` is
the real "Templates" skill and must stay.
"""

import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utilities import registry_builder


class SkillsRegistry(unittest.TestCase):
    def setUp(self):
        self.skills = registry_builder.build_skills_registry()["skills"]

    def test_the_blank_skill_template_is_not_listed(self):
        self.assertNotIn("template", {skill["id"] for skill in self.skills})
        self.assertNotIn("<Skill Name>", {skill["label"] for skill in self.skills})

    def test_the_templates_skill_is_listed(self):
        self.assertIn("templates", {skill["id"] for skill in self.skills})

    def test_every_listed_skill_has_its_file(self):
        for skill in self.skills:
            self.assertTrue(os.path.isfile(os.path.join(ROOT_DIR, skill["path"])), skill["path"])


if __name__ == "__main__":
    unittest.main()
