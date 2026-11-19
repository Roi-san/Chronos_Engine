"""Console onboarding (onboarding_wizard.bat) without its examples (issue 32).

The alpha_v0.3 repository has no example items (user/examples/ was dropped), so
the steps that cloned them must not write anything made from a missing file and
must say where the real thing is built instead. Every test works on a temporary
folder: the wizard's paths are pointed there, never at the repository's user/.
"""
import builtins
import os
import sys

import pytest
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from modules import onboarding_wizard as ow  # noqa: E402


@pytest.fixture
def wizard(tmp_path, monkeypatch):
    # The wizard themes the console by replacing builtins.print for the whole
    # process; keep that out of the test session.
    monkeypatch.setattr(ow.console_style, "enable_themed_print", lambda *a, **k: None)
    monkeypatch.setattr(ow.console_style, "apply_global_colors", lambda *a, **k: None)
    w = ow.OnboardingWizard()
    w.root = tmp_path
    w.user_dir = tmp_path / "user"
    w.settings_dir = w.user_dir / "settings"
    w.profile_path = w.user_dir / "profile" / "profile.yml"
    w.current_status_path = w.user_dir / "current_status.yml"
    w.user_dir.mkdir()
    return w


def answer_everything_with_enter(monkeypatch):
    """Press Enter at every prompt: the defaults (yes for the clone questions)."""
    monkeypatch.setattr(builtins, "input", lambda *_: "")


def files_under(folder):
    return sorted(str(p.relative_to(folder)).replace("\\", "/") for p in folder.rglob("*.yml"))


def test_template_step_writes_no_empty_day_template(wizard, monkeypatch, capsys):
    # Before: "Clone Weekday Example?" defaulted to yes and saved {name: My Weekday Flow},
    # a day template with no sleep, no blocks and no children, which Kairos could then pick.
    answer_everything_with_enter(monkeypatch)
    wizard.step_template()
    assert files_under(wizard.user_dir) == []
    out = capsys.readouterr().out
    assert "Life Setup" in out
    assert not any("day template" in change.lower() for change in wizard.changes)


def test_template_step_names_existing_day_templates(wizard, monkeypatch, capsys):
    days = wizard.user_dir / "days"
    days.mkdir()
    (days / "life_skeleton.yml").write_text(yaml.safe_dump({"name": "Life Skeleton", "type": "day", "children": []}), encoding="utf-8")
    answer_everything_with_enter(monkeypatch)
    wizard.step_template()
    out = capsys.readouterr().out
    assert "Life Skeleton" in out
    assert files_under(wizard.user_dir) == ["days/life_skeleton.yml"]


def test_template_step_still_clones_an_example_that_exists(wizard, monkeypatch):
    # Kept for a repository that ships the example again: cloning works as before.
    days = wizard.user_dir / "days"
    days.mkdir()
    example = {"name": "Weekday Example", "type": "day", "children": [{"name": "Core Sleep", "type": "timeblock"}]}
    (days / "weekday_example.yml").write_text(yaml.safe_dump(example), encoding="utf-8")
    answer_everything_with_enter(monkeypatch)
    wizard.step_template()
    copy = yaml.safe_load((days / "my-weekday-flow.yml").read_text(encoding="utf-8"))
    assert copy["name"] == "My Weekday Flow"
    assert copy["children"] == example["children"]


def test_example_steps_without_examples_point_to_the_real_tools(wizard, monkeypatch, capsys):
    answer_everything_with_enter(monkeypatch)
    wizard.ensure_examples()
    wizard.step_example_items()
    wizard.step_goal()
    wizard.step_commitment()
    out = capsys.readouterr().out
    assert files_under(wizard.user_dir) == []
    assert wizard.changes == []
    # No "consider restoring them": a new user has nothing to restore.
    assert "missing" not in out.lower()
    assert "Routine Builder" in out
    assert "Goal Planning" in out
    assert "capture" in out.lower()


def test_wrap_up_without_a_day_template_says_what_to_do_next(wizard, monkeypatch, capsys):
    wizard.wrap_up()
    out = capsys.readouterr().out
    assert "Life Setup" in out
