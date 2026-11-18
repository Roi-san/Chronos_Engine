"""What happens downstream when the day's end is exactly midnight (1440) or later?

Usage: python midnight_probe.py <export_root>

Forces day_budget.sleep_boundary_minutes to a chosen value after model_day_budget
runs, then prints the gaps and what got placed. Pure experiment, no repo changes.
"""
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

FORCED = {"value": None}


class Forced(KairosV2Scheduler):
    # Make model_day_budget itself see a sleep anchor starting at the forced
    # minute, so every budget field (remaining, open flexible) follows from it.
    def _find_primary_sleep_anchor(self, template, anchor_date):
        found = super()._find_primary_sleep_anchor(template, anchor_date)
        if FORCED["value"] is not None and found:
            found = dict(found, start_minutes=FORCED["value"])
        return found


DAY = {"name": "D", "type": "day", "children": [
    {"name": "Core Sleep", "type": "timeblock", "start_time": "02:00", "end_time": "10:30", "duration": 510, "reschedule": "never", "category": "sleep"},
    {"name": "Dinner", "type": "timeblock", "start_time": "21:00", "end_time": "21:30", "duration": 30, "reschedule": "never"},
]}
FILES = {
    "habits/stretch.yml": {"name": "Evening stretch", "type": "habit", "duration": "20m", "frequency": "daily"},
    "habits/journal.yml": {"name": "Journal", "type": "habit", "duration": "15m", "frequency": "daily"},
    "habits/walk.yml": {"name": "Night walk", "type": "habit", "duration": "60m", "frequency": "daily"},
}


def run(forced, now):
    FORCED["value"] = forced
    with temporary_kairos_user_fixture() as fixture:
        user_dir = fixture["user_dir"]
        days_dir = os.path.join(user_dir, "days")
        for name in os.listdir(days_dir):
            os.remove(os.path.join(days_dir, name))
        with open(os.path.join(days_dir, "d.yml"), "w", encoding="utf-8") as fh:
            yaml.safe_dump(DAY, fh, sort_keys=False)
        for rel, payload in FILES.items():
            p = os.path.join(user_dir, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                yaml.safe_dump(payload, fh, sort_keys=False)
        result = Forced({"now": now, "start_from_now": True}).generate_schedule(now.date())
    s = result["schedule"]
    gaps = [(g["start_time"], g["end_time"], g["start_minutes"], g["end_minutes"]) for g in s["gap_buffer_recovery"]["emergent_gaps"]]
    placements = [(p.get("start_time"), p.get("end_time"), [c["name"] for c in p.get("selected", [])]) for p in s["remaining_structure_placement"]["gap_placements"]]
    blocks = []
    for b in s["conceptual_schedule"]["conceptual_blocks"]:
        blocks.append((b.get("kind"), b.get("name"), b.get("start_time"), b.get("end_time"), b.get("start_minutes"), b.get("end_minutes"), [c.get("name") for c in b.get("children") or []]))
    units = [(u.get("name"), u.get("start_time"), u.get("end_time")) for u in s["timer_handoff"].get("execution_units", [])]
    return gaps, placements, blocks, s["remaining_structure_placement"]["overflow_items"], units


for forced in (1439, 1440, 1560):
    gaps, placements, blocks, overflow, units = run(forced, datetime(2026, 4, 16, 22, 0))
    print(f"== boundary forced to {forced} at 22:00")
    print("   gaps:", gaps)
    print("   gap placements:", placements)
    print("   conceptual blocks:")
    for b in blocks:
        print("     ", b)
    print("   overflow:", [o.get("name") for o in overflow])
    print("   timer units:", units)
