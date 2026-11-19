"""
Direction signals: what the pilot is aiming for, turned into scheduling pressure.

Kairos ranks work by category, priority, due date, deadline and happiness. This
module adds the two things that say where a life is meant to go:

- **Goals** (and their milestones): work linked to an active goal ranks higher,
  more so when the goal matters and its date is close.
- **Commitments** ("3 workouts a week"): work a commitment counts ranks higher
  the closer the period is to ending unmet. The day it becomes "today or never",
  it gets the strongest push in the system. A period missed outright adds to the
  next one.
- **Recurring items** (since roadmap step 1c, decision D2): a weekly to yearly
  habit or chore whose turn has come, and a daily one missed yesterday, get a
  push that grows as the period runs out. The rules live in recurrence.py
  (docs/scheduling/recurrence_design.md); this module loads them with the rest
  and adds their points in `bonus_for()`.

It only reads YAML and returns plain data. Kairos decides what to do with it.

Level scale: every signal carries a `level` from 0.0 (no pressure) to 1.0
(maximum). `bonus_for()` converts levels into score points.

Days, periods and "was it done" come from periods.py, the one shared helper
(step 1c). The old names below (`period_bounds`, `previous_period_bounds`,
`mini_names_for`, `_completed_names_by_date`, `_done_dates`) now point there.
"""
from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import yaml

from . import periods as Periods
from . import recurrence as Recurrence

# Score points at level 1.0, before the user's weights are applied.
#
# Calibrated against real scores with the shipped settings: a due-today item gets
# +20, a deadline-today item +25, the top category about +42 and top priority
# +20, so a high-priority work task due today lands near 66 and the theoretical
# ceiling for an ordinary item is about 107.
#
# - A commitment on its last possible day (90) outranks any ordinary due-today
#   task; one day of slack (63) sits level with the most important of them; an
#   on-track commitment (18) is a nudge about as strong as "due today".
# - Work for a high-priority goal due within three days (54) beats most of the
#   day; a goal with no date adds 6 to 21 depending on its priority.
GOAL_MAX_BONUS = 60.0
COMMITMENT_MAX_BONUS = 90.0
# Default rank (1-10) when scheduling_priorities.yml has no row for the factor.
DEFAULT_FACTOR_RANK = 5.0

INACTIVE_STATES = {
    "completed", "complete", "done", "archived", "cancelled", "canceled",
    "abandoned", "on_hold", "on hold", "paused", "inactive", "dropped",
}
LINKABLE_DIRS = {
    "task": "tasks",
    "habit": "habits",
    "routine": "routines",
    "subroutine": "subroutines",
    "microroutine": "microroutines",
}
PRIORITY_WEIGHT = {
    "critical": 1.0, "urgent": 1.0, "highest": 1.0, "high": 1.0,
    "medium": 0.6, "normal": 0.6, "moderate": 0.6,
    "low": 0.3, "lowest": 0.2,
}


# --------------------------------------------------------------------------- IO

def _lower_keys(value: Any) -> Any:
    """Lowercase mapping keys recursively. Default files use `Rule: {Kind: ...}`."""
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, inner in value.items():
            if isinstance(key, str) and key == key.lower():
                out[key] = _lower_keys(inner)
        for key, inner in value.items():
            lowered = str(key).lower()
            if lowered not in out:
                out[lowered] = _lower_keys(inner)
        return out
    if isinstance(value, list):
        return [_lower_keys(entry) for entry in value]
    return value


def _read_dir(user_dir: str, dirname: str) -> List[Dict[str, Any]]:
    folder = os.path.join(user_dir, dirname)
    items: List[Dict[str, Any]] = []
    if not os.path.isdir(folder):
        return items
    for filename in sorted(os.listdir(folder)):
        if not filename.endswith(".yml"):
            continue
        try:
            with open(os.path.join(folder, filename), "r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle)
        except Exception:
            continue
        if isinstance(payload, dict):
            item = _lower_keys(payload)
            if str(item.get("name") or "").strip():
                items.append(item)
    return items


def _token(value: Any) -> str:
    return str(value or "").strip().lower()


def _identity(item_type: Any, name: Any) -> str:
    item_type = _token(item_type)
    name = _token(name)
    return f"{item_type}:{name}" if item_type and name else ""


def _parse_date(value: Any) -> Optional[date]:
    if isinstance(value, date):
        return value
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _is_active(item: Dict[str, Any]) -> bool:
    return _token(item.get("status")) not in INACTIVE_STATES


# Moved to periods.py in step 1c (the same answers; tests/test_periods.py compares
# them with frozen copies of the old code). The old names stay for callers.
_completed_names_by_date = Periods.completed_names_by_date


# ----------------------------------------------------------------------- periods

# Moved to periods.py in step 1c. Same answers for day, week and month, and for
# anything that is not a period (a week). New: quarter and year, and the words
# daily / weekly / monthly / quarterly / yearly (before, all of these were read
# as a week).
period_bounds = Periods.period_bounds
previous_period_bounds = Periods.previous_period_bounds


# ------------------------------------------------------------------- commitments

def _rule(commitment: Dict[str, Any]) -> Tuple[str, int, str]:
    rule = commitment.get("rule") if isinstance(commitment.get("rule"), dict) else {}
    kind = _token(rule.get("kind"))
    times = rule.get("times")
    period = _token(rule.get("period"))
    if not kind:
        freq = commitment.get("frequency") if isinstance(commitment.get("frequency"), dict) else None
        if freq:
            kind, times, period = "frequency", freq.get("times"), _token(freq.get("period"))
        elif commitment.get("never"):
            kind = "never"
    try:
        times = int(times or 0)
    except (TypeError, ValueError):
        times = 0
    return kind, times, period or "week"


def _targets(commitment: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("targets", "associated_items"):
        rows = commitment.get(key)
        if isinstance(rows, list) and rows:
            return [row for row in rows if isinstance(row, dict) and _identity(row.get("type"), row.get("name"))]
    freq = commitment.get("frequency") if isinstance(commitment.get("frequency"), dict) else {}
    of = freq.get("of") if isinstance(freq, dict) else None
    if isinstance(of, dict) and _identity(of.get("type"), of.get("name")):
        return [of]
    linked = commitment.get("linked_habit")
    if _token(linked):
        return [{"type": "habit", "name": str(linked).strip()}]
    return []


# Moved to periods.py in step 1c, unchanged: "was it done" (lighter versions
# included) is one shared question for commitments and recurring items alike.
mini_names_for = Periods.mini_names_for
_done_dates = Periods.done_dates


def evaluate_commitment(
    commitment: Dict[str, Any],
    *,
    target_date: date,
    library_by_identity: Dict[str, Dict[str, Any]],
    library_by_name: Dict[str, Dict[str, Any]],
    completed_by_date: Dict[date, set],
) -> Optional[Dict[str, Any]]:
    """
    Where a frequency commitment stands on `target_date`, and how hard to push.

    A scaled-down version of a target (its mini) counts toward the commitment:
    stretching at home on a sick day keeps "3 workouts a week" alive.
    """
    kind, times, period = _rule(commitment)
    targets = _targets(commitment)
    if kind != "frequency" or not targets:
        return None

    start, end = period_bounds(target_date, period)
    prev_start, prev_end = previous_period_bounds(target_date, period)
    days_left = (end - target_date).days + 1
    per_target = any(row.get("count") is not None for row in targets)
    library = list(library_by_name.values())

    rows = []
    for row in targets:
        identity = _identity(row.get("type"), row.get("name"))
        item = library_by_identity.get(identity)
        names = [_token(row.get("name"))] + mini_names_for(item, library)
        days = _done_dates(item, names, library_by_name, completed_by_date)
        try:
            required = max(1, int(row.get("count") if row.get("count") is not None else 1))
        except (TypeError, ValueError):
            required = 1
        rows.append({
            "identity": identity,
            "name": str(row.get("name")).strip(),
            "type": _token(row.get("type")),
            "required": required,
            "progress": sum(1 for day in days if start <= day <= target_date),
            "previous": sum(1 for day in days if prev_start <= day <= prev_end),
            "done_today": target_date in days,
            "has_history": any(day < start for day in days),
            "exists": item is not None,
        })

    if per_target:
        required_total = sum(row["required"] for row in rows)
        progress = sum(min(row["progress"], row["required"]) for row in rows)
        previous_met = all(row["previous"] >= row["required"] for row in rows)
    else:
        required_total = times
        progress = sum(row["progress"] for row in rows)
        previous_met = sum(row["previous"] for row in rows) >= times
    if required_total <= 0:
        return None

    remaining = max(0, required_total - progress)
    slack = days_left - remaining
    # Only call the last period "missed" when the commitment demonstrably existed then.
    missed_previous = (not previous_met) and any(row["has_history"] for row in rows)

    if remaining <= 0:
        state, level = "met", 0.0
    elif slack < 0:
        state, level = "behind", 1.0
    elif slack == 0:
        state, level = "last_chance", 1.0
    elif slack == 1:
        state, level = "at_risk", 0.7
    elif slack == 2:
        state, level = "tightening", 0.45
    else:
        state, level = "on_track", 0.2
    if remaining > 0 and missed_previous:
        level = min(1.0, level + 0.2)

    unit = {"day": "today", "week": "this week", "month": "this month"}.get(period, f"this {period}")
    if state == "met":
        reason = f"{progress} of {required_total} done {unit}"
    else:
        tail = {
            "behind": "cannot fully catch up now, so every one counts",
            "last_chance": "today is the last chance" if days_left == 1 else "needs one every remaining day",
            "at_risk": "only one day to spare",
            "tightening": "two days to spare",
            "on_track": "on track",
        }[state]
        if period == "day":
            reason = f"{progress} of {required_total} done today: still to do today"
        else:
            left = "last day" if days_left == 1 else f"{days_left} days left"
            reason = f"{progress} of {required_total} done {unit}, {left}: {tail}"
        if missed_previous:
            reason += "; missed last time"

    # How many must happen today for the period to still work out.
    need_today = 0 if remaining <= 0 else max(1, remaining - (days_left - 1))
    return {
        "name": str(commitment.get("name")).strip(),
        "period": period,
        "required": required_total,
        "progress": progress,
        "remaining": remaining,
        "days_left": days_left,
        "slack": slack,
        "state": state,
        "level": round(level, 3),
        "missed_previous": missed_previous,
        "need_today": need_today,
        "per_target": per_target,
        "reason": reason,
        "targets": rows,
    }


# ------------------------------------------------------------------------- goals

def _goal_level(priority: Any, days_left: Optional[int]) -> float:
    weight = PRIORITY_WEIGHT.get(_token(priority), 0.5)
    base = 0.35 * weight
    if days_left is None:
        urgency = 0.0
    elif days_left <= 0:
        urgency = 0.65
    elif days_left <= 3:
        urgency = 0.55
    elif days_left <= 7:
        urgency = 0.4
    elif days_left <= 14:
        urgency = 0.25
    elif days_left <= 30:
        urgency = 0.12
    else:
        urgency = 0.0
    return round(min(1.0, base + urgency), 3)


def _goal_reason(goal_name: str, via: str, due: Optional[date], days_left: Optional[int]) -> str:
    if due is None:
        when = "no date set"
    elif days_left < 0:
        when = f"{-days_left} day{'s' if days_left != -1 else ''} overdue"
    elif days_left == 0:
        when = "due today"
    else:
        when = f"due in {days_left} day{'s' if days_left != 1 else ''}"
    return f"Serves goal \"{goal_name}\" ({via}, {when})"


# -------------------------------------------------------------------------- main

def load_direction(user_dir: str, target_date: date) -> Dict[str, Any]:
    """
    Build every direction signal for `target_date`.

    Returns:
      by_identity: { "habit:gym session": {"goal": {...}?, "commitment": {...}?} }
      goals:        active goals with their nearest date
      commitments:  evaluated frequency commitments
    """
    library: List[Dict[str, Any]] = []
    for item_type, dirname in LINKABLE_DIRS.items():
        for item in _read_dir(user_dir, dirname):
            item.setdefault("type", item_type)
            library.append(item)
    library_by_identity = {_identity(item.get("type"), item.get("name")): item for item in library}
    library_by_name: Dict[str, Dict[str, Any]] = {}
    for item in library:
        library_by_name.setdefault(_token(item.get("name")), item)

    by_identity: Dict[str, Dict[str, Any]] = {}

    # ---- goals
    goals = {_token(g.get("name")): g for g in _read_dir(user_dir, "goals") if _is_active(g)}
    goal_rows: Dict[str, Dict[str, Any]] = {}
    for key, goal in goals.items():
        due = _parse_date(goal.get("due_date") or goal.get("target_date") or goal.get("deadline"))
        goal_rows[key] = {
            "name": str(goal.get("name")).strip(),
            "priority": goal.get("priority"),
            "due": due,
            "links": 0,
        }

    def link(identity: str, goal_key: str, via: str, due_override: Optional[date] = None) -> None:
        row = goal_rows.get(goal_key)
        if not identity or row is None or identity not in library_by_identity:
            return
        if not _is_active(library_by_identity[identity]):
            return
        dues = [d for d in (row["due"], due_override) if d]
        due = min(dues) if dues else None
        days_left = (due - target_date).days if due else None
        level = _goal_level(row["priority"], days_left)
        signal = {
            "name": row["name"],
            "via": via,
            "due": due.isoformat() if due else None,
            "days_left": days_left,
            "level": level,
            "reason": _goal_reason(row["name"], via, due, days_left),
        }
        row["links"] += 1
        current = by_identity.setdefault(identity, {}).get("goal")
        if current is None or signal["level"] > current["level"]:
            by_identity[identity]["goal"] = signal

    projects = {_token(p.get("name")): p for p in _read_dir(user_dir, "projects") if _is_active(p)}
    for item in library:
        identity = _identity(item.get("type"), item.get("name"))
        goal_key = _token(item.get("goal"))
        if goal_key:
            link(identity, goal_key, "linked directly")
        project = projects.get(_token(item.get("project")))
        if project and _token(project.get("goal")):
            link(identity, _token(project.get("goal")), f"project \"{project.get('name')}\"")

    for key, goal in goals.items():
        for name in goal.get("supporting_habits") or []:
            link(_identity("habit", name), key, "supporting habit")

    for milestone in _read_dir(user_dir, "milestones"):
        goal_key = _token(milestone.get("goal"))
        if goal_key not in goal_rows or not _is_active(milestone):
            continue
        due = _parse_date(milestone.get("due_date") or milestone.get("target_date"))
        via = f"milestone \"{milestone.get('name')}\""
        criteria = milestone.get("criteria") if isinstance(milestone.get("criteria"), dict) else {}
        refs: List[Any] = []
        count = criteria.get("count") if isinstance(criteria.get("count"), dict) else {}
        if isinstance(count.get("of"), dict):
            refs.append(count["of"])
        checklist = criteria.get("checklist") if isinstance(criteria.get("checklist"), dict) else {}
        refs.extend(checklist.get("items") or [])
        refs.extend(milestone.get("links") or [])
        for ref in refs:
            if isinstance(ref, dict):
                link(_identity(ref.get("type"), ref.get("name")), goal_key, via, due)

    # ---- the completion logs, read once for commitments and recurring items
    commitments = [c for c in _read_dir(user_dir, "commitments") if _is_active(c)]
    # Before step 1c the window was the previous week and month; it still is,
    # widened for quarter and year commitments and for recurring items.
    window = [previous_period_bounds(target_date, "month")[0], previous_period_bounds(target_date, "week")[0]]
    window.extend(previous_period_bounds(target_date, _rule(c)[2])[0] for c in commitments)
    # A failure in recurring items must never cost goals and commitments: Kairos
    # then shows every once-per-period item (its fallback) and says so.
    recurring_items: Optional[List[Dict[str, Any]]] = None
    recurring_error: Optional[str] = None
    try:
        recurring_items = Recurrence.read_library(user_dir)
        window.append(Recurrence.log_window_start(target_date, recurring_items))
    except Exception as exc:
        recurring_items, recurring_error = None, str(exc)
    completed_by_date = _completed_names_by_date(user_dir, min(window), target_date)

    # ---- commitments
    commitment_rows: List[Dict[str, Any]] = []
    for commitment in commitments:
        status = evaluate_commitment(
            commitment,
            target_date=target_date,
            library_by_identity=library_by_identity,
            library_by_name=library_by_name,
            completed_by_date=completed_by_date,
        )
        if status is None:
            continue
        commitment_rows.append(status)
        if status["level"] <= 0:
            continue
        # With interchangeable targets ("gym or run, 3 a week") only as many as are
        # needed today get the full push; the rest stay available at a low level.
        open_rows = [row for row in status["targets"] if row["exists"] and not row["done_today"]]
        if status["per_target"]:
            open_rows = [row for row in open_rows if row["progress"] < row["required"]]
        for index, row in enumerate(open_rows):
            full = status["per_target"] or index < status["need_today"]
            level = status["level"] if full else min(status["level"], 0.2)
            signal = {
                "name": status["name"],
                "state": status["state"],
                "level": round(level, 3),
                "progress": status["progress"],
                "required": status["required"],
                "days_left": status["days_left"],
                "reason": f"Counts toward \"{status['name']}\" ({status['reason']})",
            }
            current = by_identity.setdefault(row["identity"], {}).get("commitment")
            if current is None or signal["level"] > current["level"]:
                by_identity[row["identity"]]["commitment"] = signal

    # ---- recurring items (decision D2, recurrence.py)
    # `recurring.by_identity` holds every recurring item's status: Kairos reads
    # it to decide what is on today's plan. Only items with a push today (a turn
    # that has come, a daily item missed yesterday) also get a signal here.
    recurring: Dict[str, Any] = {"by_identity": {}, "unrecognised": [], "error": recurring_error}
    if recurring_items is not None:
        try:
            # Turns skipped for the whole period (D9) over the same window.
            skipped_by_date = Periods.turn_skips_by_date(user_dir, min(window), target_date)
            recurring = Recurrence.evaluate_library(recurring_items, target_date, completed_by_date, skipped_by_date)
        except Exception as exc:
            recurring = {"by_identity": {}, "unrecognised": [], "error": str(exc)}
    for identity, status in (recurring.get("by_identity") or {}).items():
        signal = Recurrence.pressure_signal(status)
        if signal:
            by_identity.setdefault(identity, {})["recurring"] = signal

    return {
        "by_identity": by_identity,
        "goals": [
            {
                "name": row["name"],
                "priority": row["priority"],
                "due": row["due"].isoformat() if row["due"] else None,
                "days_left": (row["due"] - target_date).days if row["due"] else None,
                "linked_items": row["links"],
            }
            for row in goal_rows.values()
        ],
        "commitments": commitment_rows,
        "recurring": recurring,
    }


def bonus_for(signal: Optional[Dict[str, Any]], factor_weights: Optional[Dict[str, float]] = None) -> float:
    """
    Score points for one candidate's direction signal.

    `factor_weights` is Kairos's map from scheduling_priorities.yml. The rows
    "Goal Alignment", "Commitment Pressure" and "Recurring Pressure" scale these
    bonuses; rank 5 is neutral, 10 doubles, 0 switches the factor off.
    """
    if not isinstance(signal, dict):
        return 0.0
    weights = factor_weights or {}
    total = 0.0
    goal = signal.get("goal")
    if isinstance(goal, dict):
        factor = float(weights.get("goal_alignment", DEFAULT_FACTOR_RANK)) / DEFAULT_FACTOR_RANK
        total += GOAL_MAX_BONUS * float(goal.get("level") or 0.0) * factor
    commitment = signal.get("commitment")
    if isinstance(commitment, dict):
        factor = float(weights.get("commitment_pressure", DEFAULT_FACTOR_RANK)) / DEFAULT_FACTOR_RANK
        total += COMMITMENT_MAX_BONUS * float(commitment.get("level") or 0.0) * factor
    recurring = signal.get("recurring")
    if isinstance(recurring, dict):
        factor = float(weights.get(Recurrence.WEIGHT_NAME, DEFAULT_FACTOR_RANK)) / DEFAULT_FACTOR_RANK
        total += Recurrence.RECURRING_MAX_BONUS * float(recurring.get("level") or 0.0) * factor
    return total


def is_strong(signal: Optional[Dict[str, Any]]) -> bool:
    """Pressure strong enough to justify opening a helper window for the item."""
    if not isinstance(signal, dict):
        return False
    commitment = signal.get("commitment") or {}
    goal = signal.get("goal") or {}
    return float(commitment.get("level") or 0.0) >= 0.7 or float(goal.get("level") or 0.0) >= 0.5
