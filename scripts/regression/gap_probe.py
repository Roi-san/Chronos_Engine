"""Issue 2 probe: where does Kairos put work around a fixed slot, and how tightly?

Usage: python gap_probe.py <export_root> [--json]
Runs on the repo's temporary test fixture inside the export, never the real user/ folder.
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

D = (2026, 4, 16)


def sleep(start="23:55", minutes=480):
    return {"name": "Sleep", "type": "timeblock", "sleep": True, "reschedule": "never", "start_time": start, "duration": minutes}


def gym_slot(start="22:30", minutes=45):
    return {"name": "Gym", "type": "habit", "start_time": start, "duration": minutes}


def anchor(name, start, end, minutes):
    return {"name": name, "type": "timeblock", "start_time": start, "end_time": end, "duration": minutes, "reschedule": "never"}


def task(name, minutes, **extra):
    return {"name": name, "type": "task", "duration": f"{minutes}m", **extra}


def habit(name, minutes, **extra):
    return {"name": name, "type": "habit", "duration": f"{minutes}m", "frequency": "daily", **extra}


def run(children, files, now, context=None):
    with temporary_kairos_user_fixture() as fixture:
        user_dir = fixture["user_dir"]
        days_dir = os.path.join(user_dir, "days")
        for name in os.listdir(days_dir):
            os.remove(os.path.join(days_dir, name))
        # The base fixture's daily "Stretch Break" habit would add noise; remove it.
        for rel in ("habits/stretch_break.yml",):
            p = os.path.join(user_dir, rel)
            if os.path.exists(p):
                os.remove(p)
        with open(os.path.join(days_dir, "d.yml"), "w", encoding="utf-8") as fh:
            yaml.safe_dump({"name": "Day", "type": "day", "children": children}, fh, sort_keys=False)
        for rel, payload in files.items():
            p = os.path.join(user_dir, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                yaml.safe_dump(payload, fh, sort_keys=False)
        result = KairosV2Scheduler({"now": now, "start_from_now": True, **(context or {})}).generate_schedule(now.date())
    s = result["schedule"]
    placed = []
    for b in s["conceptual_schedule"]["conceptual_blocks"]:
        kids = b.get("children") or []
        if kids:
            for c in kids:
                placed.append(f"{c.get('start_time')}-{c.get('end_time')} {c.get('name')} (in {b.get('kind')}: {b.get('name')})")
        else:
            placed.append(f"{b.get('start_time')}-{b.get('end_time')} {b.get('name')} [{b.get('kind')}]")
    gaps = [f"{g['start_time']}-{g['end_time']} ({g['duration_minutes']}m)" for g in s["gap_buffer_recovery"].get("base_emergent_gaps", s["gap_buffer_recovery"]["emergent_gaps"])]
    helpers = [f"{w.get('window_name')} {w.get('start_time')}-{w.get('end_time')}" for w in s["runtime_helper_windows"].get("windows", [])]
    return {"gaps_before_helpers": gaps, "helper_windows": helpers, "placed": placed,
            "overflow": [o.get("name") for o in s["remaining_structure_placement"].get("overflow_items", [])]}


TODAY = "2026-04-16"
at = lambda h, m=0: datetime(*D, h, m)  # noqa: E731
SCENARIOS = {
    "1 the 2026-11-17 case: 20m task, deadline today, 22:05, Gym fixed 22:30": (
        [sleep(), gym_slot()], {"tasks/taxes.yml": task("File taxes", 20, deadline=TODAY)}, at(22, 5)),
    "2 same, but due today instead of deadline": (
        [sleep(), gym_slot()], {"tasks/taxes.yml": task("File taxes", 20, due_date=TODAY)}, at(22, 5)),
    "3 same, but a daily habit (no date)": (
        [sleep(), gym_slot()], {"habits/tidy.yml": habit("Tidy desk", 20)}, at(22, 5)),
    "4 deadline task + daily habit together": (
        [sleep(), gym_slot()], {"tasks/taxes.yml": task("File taxes", 20, deadline=TODAY), "habits/tidy.yml": habit("Tidy desk", 20)}, at(22, 5)),
    "5 deadline task, only small gaps (Gym 22:30-23:40, sleep 23:55)": (
        [sleep(), gym_slot("22:30", 70)], {"tasks/taxes.yml": task("File taxes", 20, deadline=TODAY)}, at(22, 5)),
    "6 morning: 25m gap before a 09:00 meeting, next big gap after lunch": (
        [sleep(), anchor("Meeting", "09:00", "12:30", 210), anchor("Lunch", "12:30", "13:30", 60)],
        {"tasks/report.yml": task("Send report", 20, due_date=TODAY)}, at(8, 35)),
    "7 light day: 11:00, three habits, whole afternoon free": (
        [sleep(), anchor("Lunch", "13:00", "13:30", 30)],
        {"habits/a.yml": habit("Read", 30), "habits/b.yml": habit("Walk", 30), "habits/c.yml": habit("Journal", 15)}, at(11, 0)),
}

if __name__ == "__main__":
    out = {label: run(*args) for label, args in SCENARIOS.items()}
    if "--json" in sys.argv:
        print(json.dumps(out, indent=1, sort_keys=True))
    else:
        for label, row in out.items():
            print(f"== {label}")
            print(f"   gaps: {row['gaps_before_helpers']}")
            if row["helper_windows"]:
                print(f"   helper windows: {row['helper_windows']}")
            for p in row["placed"]:
                print(f"     {p}")
            if row["overflow"]:
                print(f"   overflow: {row['overflow']}")
