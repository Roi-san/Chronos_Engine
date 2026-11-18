"""Probe how Kairos v2 ends the day for different sleep anchors and clock times.

Usage: python sleep_probe.py <export_root> [--json]

Runs each scenario on the repo's own temporary test fixture inside the export
(never the real user/ folder) and prints the day budget and what was placed.
"""
import json
import os
import sys
from datetime import datetime

ROOT = os.path.abspath(sys.argv[1])
os.chdir(ROOT)
for path in (ROOT, os.path.join(ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

import yaml  # noqa: E402

from chronos_fixture import temporary_kairos_user_fixture  # noqa: E402
from modules.scheduler.kairos_v2 import KairosV2Scheduler  # noqa: E402


def sleep_node(start, end=None, duration=None, name="Core Sleep"):
    node = {"name": name, "type": "timeblock", "start_time": start, "reschedule": "never", "category": "sleep"}
    if end:
        node["end_time"] = end
    if duration is not None:
        node["duration"] = duration
    return node


# The pilot's real Life Skeleton shape (times only), plus one flexible task.
def life_skeleton(sleep):
    children = [sleep] if sleep else []
    children += [
        {"name": "Breakfast", "type": "timeblock", "start_time": "11:00", "end_time": "11:15", "duration": 15, "reschedule": "never"},
        {"name": "Work", "type": "timeblock", "start_time": "12:00", "end_time": "15:00", "duration": 180, "reschedule": "never"},
        {"name": "Dinner", "type": "timeblock", "start_time": "21:00", "end_time": "21:30", "duration": 30, "reschedule": "never"},
    ]
    return {"name": "Life Skeleton", "type": "day", "children": children}


TASKS = {
    "tasks/read.yml": {"name": "Read a chapter", "type": "task", "duration": "45m", "due_date": None},
    "habits/stretch.yml": {"name": "Evening stretch", "type": "habit", "duration": "20m", "frequency": "daily"},
    "habits/journal.yml": {"name": "Journal", "type": "habit", "duration": "15m", "frequency": "daily"},
}


def run(day, now, context=None):
    with temporary_kairos_user_fixture() as fixture:
        user_dir = fixture["user_dir"]
        days_dir = os.path.join(user_dir, "days")
        for name in os.listdir(days_dir):
            os.remove(os.path.join(days_dir, name))
        with open(os.path.join(days_dir, "day.yml"), "w", encoding="utf-8") as fh:
            yaml.safe_dump(day, fh, sort_keys=False)
        for rel, payload in TASKS.items():
            payload = dict(payload)
            if payload.get("due_date") is None and payload.get("type") == "task":
                payload["due_date"] = now.date().isoformat()
            path = os.path.join(user_dir, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                yaml.safe_dump(payload, fh, sort_keys=False)
        result = KairosV2Scheduler({"now": now, **(context or {})}).generate_schedule(now.date())
    schedule = result.get("schedule", {})
    blocks = []
    for block in schedule.get("conceptual_schedule", {}).get("conceptual_blocks", []):
        kids = block.get("children") or []
        if kids:
            for child in kids:
                blocks.append(f"{child.get('start_time')}-{child.get('end_time')} {child.get('name')}")
        else:
            blocks.append(f"{block.get('start_time')}-{block.get('end_time')} {block.get('name')} [{block.get('kind')}]")
    budget = schedule.get("day_budget", {})
    commit = schedule.get("sleep_commitment", {})
    gaps = schedule.get("gap_buffer_recovery", {}).get("emergent_gaps", [])
    overflow = schedule.get("remaining_structure_placement", {}).get("overflow_items", [])
    return {
        "budget": {k: budget.get(k) for k in ("sleep_boundary_time", "sleep_boundary_minutes", "sleep_boundary_source", "remaining_minutes_before_sleep", "open_flexible_minutes_before_sleep")},
        "sleep_state": commit.get("current_day_state"),
        "gaps": [f"{g.get('start_time')}-{g.get('end_time')} ({g.get('duration_minutes')}m)" for g in gaps],
        "placed": blocks,
        "overflow": [o.get("name") for o in overflow],
    }


D = (2026, 4, 16)  # Thursday, the fixture's day
SCENARIOS = [
    ("A  sleep 02:00-10:30 (pilot's shape), 11:00", life_skeleton(sleep_node("02:00", "10:30", 510)), datetime(*D, 11, 0), {"start_from_now": True}),
    ("B  sleep 02:00-10:30, 22:00", life_skeleton(sleep_node("02:00", "10:30", 510)), datetime(*D, 22, 0), {"start_from_now": True}),
    ("C  sleep 02:00-10:30, 00:30 (after midnight, before bed)", life_skeleton(sleep_node("02:00", "10:30", 510)), datetime(*D, 0, 30), {"start_from_now": True}),
    ("D  sleep 02:00-10:30, 03:00 inside sleep, stay_awake", life_skeleton(sleep_node("02:00", "10:30", 510)), datetime(*D, 3, 0), {"start_from_now": True, "sleep_policy": "stay_awake"}),
    ("E  sleep 02:00-10:30, 03:00 inside sleep, go_back_to_sleep", life_skeleton(sleep_node("02:00", "10:30", 510)), datetime(*D, 3, 0), {"start_from_now": True, "sleep_policy": "go_back_to_sleep"}),
    ("F  sleep 00:30 + 450m (last night's repro), 22:04", life_skeleton(sleep_node("00:30", duration=450, name="Sleep")), datetime(*D, 22, 4), {"start_from_now": True}),
    ("G  sleep 00:00-08:00 (midnight), 20:00", life_skeleton(sleep_node("00:00", "08:00", 480)), datetime(*D, 20, 0), {"start_from_now": True}),
    ("H  sleep 23:30-07:30 (control), 22:00", life_skeleton(sleep_node("23:30", "07:30", 480)), datetime(*D, 22, 0), {"start_from_now": True}),
    ("I  sleep 23:30-07:30 (control), 11:00", life_skeleton(sleep_node("23:30", "07:30", 480)), datetime(*D, 11, 0), {"start_from_now": True}),
    ("J  no sleep anchor (fallback), 22:00", life_skeleton(None), datetime(*D, 22, 0), {"start_from_now": True}),
    ("K  no sleep anchor (fallback), 11:00", life_skeleton(None), datetime(*D, 11, 0), {"start_from_now": True}),
    ("L  nap 14:00-15:00 + sleep 23:00-07:00 (biphasic), 11:00", {"name": "Bi", "type": "day", "children": [
        sleep_node("23:00", "07:00", 480), sleep_node("14:00", "15:00", 60, name="Second Sleep")]}, datetime(*D, 11, 0), {"start_from_now": True}),
]

if __name__ == "__main__":
    out = {}
    for label, day, now, ctx in SCENARIOS:
        out[label] = run(day, now, ctx)
    if "--json" in sys.argv:
        print(json.dumps(out, indent=1, sort_keys=True))
    else:
        for label, row in out.items():
            print(f"== {label}")
            print(f"   budget: {row['budget']}  sleep_state={row['sleep_state']}")
            print(f"   gaps: {row['gaps']}")
            print(f"   placed: {row['placed']}")
            if row["overflow"]:
                print(f"   overflow: {row['overflow']}")
