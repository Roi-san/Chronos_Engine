"""
What counts as sleep: one rule for all of Chronos (decision D5, 2026-11-19).

Design: `docs/scheduling/planning_and_tracking_model.md`, proposal A. Issues 38,
43 and 46 in `docs/ISSUES_AND_NEXT_STEPS.md`.

The rule
--------
Only a **block on a day template** can be sleep. A block is sleep when it is
*marked* as sleep, the way the wizards mark it:

- Life Setup: `category: sleep`, `tags: [anchor, sleep]`, `reschedule: never`;
- the Sleep Settings widget: `sleep: true`, `category: sleep`, `tags: [anchor, sleep]`
  (without `reschedule: never`: a sleep block is fixed by nature).

Habits, routines, microroutines, tasks and every other item are ordinary work,
whatever their name, category, tags or `sleep` flag. A "Bedtime Routine" and an
"Evening Wind-down" with the same steps are planned the same way, and so is the
Sleep Settings wizard's wind-down pack (microroutines it marks `sleep: true`).

One fallback keeps old and hand-written templates working: on a day where **no**
block is marked, a *fixed* timeblock whose name contains "sleep" is the sleep
block. Kairos records when it used the fallback (`schedule.sleep_blocks.by_name`).

Before 2026-11-19 five places guessed sleep from the name ("sleep" or "bedtime"
anywhere in it) or from any mark on any item: `kairos_v2._is_sleep_like_node`,
`kairos_v2._looks_like_sleep_entry`, `sleep_gate._is_sleep_anchor`, and the tray
app's notification title. The first three use this module now. The tray app
(`utilities/tray/app.py`, `_is_sleep_block`) still picks its notification title
("Bedtime Soon" or "Upcoming Anchor") from the name; it changes only that wording,
never a plan, and the planned blocks it reads do not carry the marks.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

# Item types that can be a sleep block. Everything else is work.
SLEEP_BLOCK_TYPES = frozenset({"", "timeblock"})


def _token(value: Any) -> str:
    return str(value or "").strip().lower()


def _tags(node: Dict[str, Any]) -> set:
    raw = node.get("tags")
    if isinstance(raw, str):
        raw = [part for part in raw.replace(";", ",").split(",")]
    if not isinstance(raw, (list, tuple, set)):
        return set()
    return {_token(tag) for tag in raw if _token(tag)}


def _is_block(node: Any) -> bool:
    return isinstance(node, dict) and _token(node.get("type")) in SLEEP_BLOCK_TYPES


def is_fixed(node: Dict[str, Any]) -> bool:
    """Fixed in time: `reschedule: never`, `anchored: true`, subtype anchor, or essential."""
    if not isinstance(node, dict):
        return False
    return (
        _token(node.get("reschedule")) == "never"
        or node.get("anchored") is True
        or _token(node.get("subtype") or node.get("timeblock_subtype")) == "anchor"
        or node.get("essential") is True
    )


def is_marked_sleep_block(node: Any) -> bool:
    """A block marked as sleep (`sleep: true`, or category or tag `sleep`)."""
    if not _is_block(node):
        return False
    return node.get("sleep") is True or _token(node.get("category")) == "sleep" or "sleep" in _tags(node)


def is_named_sleep_block(node: Any) -> bool:
    """The fallback shape: a fixed block, not marked, whose name contains "sleep"."""
    return _is_block(node) and is_fixed(node) and "sleep" in _token(node.get("name"))


def walk(nodes: Any) -> List[Dict[str, Any]]:
    """Every node of a template's children, nested ones included, in order."""
    out: List[Dict[str, Any]] = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        out.append(node)
        children = node.get("children")
        if isinstance(children, list):
            out.extend(walk(children))
    return out


def template_sleep_blocks(children: Iterable[Any]) -> List[Dict[str, Any]]:
    """The sleep blocks of one day template (its `children`): marked ones, else named fixed ones."""
    nodes = walk(list(children or []))
    marked = [node for node in nodes if is_marked_sleep_block(node)]
    if marked:
        return marked
    return [node for node in nodes if is_named_sleep_block(node)]


def uses_name_fallback(children: Iterable[Any]) -> bool:
    """True when the template's sleep blocks were found by name (no block is marked)."""
    nodes = walk(list(children or []))
    return not any(is_marked_sleep_block(node) for node in nodes) and any(is_named_sleep_block(node) for node in nodes)


def is_sleep_block_of(node: Any, children: Iterable[Any]) -> bool:
    """Whether `node` is one of the sleep blocks of the template whose children are given."""
    if not _is_block(node):
        return False
    return any(node is block or node == block for block in template_sleep_blocks(children))


def is_sleep_log_entry(entry: Any, sleep_block_names: Iterable[str]) -> bool:
    """
    Whether a completion-log entry records sleep: it carries a sleep mark, or it is
    named like one of the sleep blocks of the user's day templates. A finished
    "Bedtime Routine" is not sleep.
    """
    if not isinstance(entry, dict):
        return False
    if entry.get("sleep") is True or _token(entry.get("category")) == "sleep" or "sleep" in _tags(entry):
        return True
    name = _token(entry.get("name") or entry.get("item_name"))
    return bool(name) and name in {_token(n) for n in sleep_block_names}
