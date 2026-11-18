"""
Four weeks with all 26 chores of the Chore Setup wizard (roadmap step 1c, decision D2).

The chores are set up on Monday 16 November 2026 (`created` that day, as the wizard
writes it). Every day Kairos plans the day at 08:00; the fake user does every chore
that is planned, except the ones in SKIPS on those days, and the next day is planned
with that history. Prints, per day, the once-per-period chores on the plan (with
their state) and how many daily chores there were, then a summary.

What it shows: no day gets a wall of chores; a chore whose turn has passed when it
is set up starts next period instead of counting as missed; a skipped chore comes
back every day until done (and never into the next period); everything is done
once per period. Usage: python scripts/regression/chores_month.py <export>
"""
import contextlib
import io
import os
import sys
from datetime import date, datetime, timedelta

import yaml

root = sys.argv[1]
sys.path[:0] = [root, os.path.join(root, "tests")]
os.chdir(root)
from chronos_fixture import temporary_kairos_user_fixture  # noqa: E402
from modules.scheduler.kairos_v2 import KairosV2Scheduler  # noqa: E402

# The wizard's built-in chores (utilities/dashboard/wizards/chore_setup/index.js), minutes.
CHORES = {
    "Make Bed": ("daily", 5), "Wash Dishes": ("daily", 15), "Wipe Kitchen Counters": ("daily", 5),
    "Quick Tidy Common Area": ("daily", 10), "Sort Mail": ("daily", 5),
    "Laundry": ("weekly", 60), "Vacuum Floors": ("weekly", 30), "Clean Bathroom": ("weekly", 30),
    "Change Bed Sheets": ("weekly", 15), "Take Out Trash and Recycling": ("weekly", 10),
    "Mop Floors": ("weekly", 30), "Water Houseplants": ("weekly", 15),
    "Deep Clean Fridge": ("monthly", 30), "Clean Microwave and Oven": ("monthly", 30),
    "Dust Fans and Baseboards": ("monthly", 30), "Wash Windows": ("monthly", 45),
    "Clean Shower Drain": ("monthly", 15), "Organize Pantry": ("monthly", 30),
    "Replace HVAC Filter": ("quarterly", 15), "Rotate Mattress": ("quarterly", 20),
    "Deep Declutter Closet": ("quarterly", 45), "Clean Behind Appliances": ("quarterly", 45),
    "Test Smoke and CO Alarms": ("yearly", 20), "Clean Dryer Vent": ("yearly", 30),
    "Deep Clean Carpets": ("yearly", 90), "Review Home Emergency Kit": ("yearly", 30),
}
SETUP = date(2026, 11, 16)                    # a Monday
DAYS = [SETUP + timedelta(days=i) for i in range(28)]
# Missed on purpose: Laundry on its turn and the day after; Vacuum Floors all its first week.
SKIPS = {SETUP + timedelta(days=i): {"Vacuum Floors"} for i in range(7)}
for missed in (date(2026, 11, 18), date(2026, 11, 19)):
    SKIPS[missed] = SKIPS[missed] | {"Laundry"}
DAY_TEMPLATE = {"name": "Chore Day", "type": "day", "children": [
    {"name": "Sleep", "type": "timeblock", "sleep": True, "reschedule": "never", "start_time": "23:00", "duration": 480},
    {"name": "Work", "type": "timeblock", "reschedule": "never", "start_time": "09:00", "end_time": "17:00"},
    {"name": "Dinner", "type": "timeblock", "reschedule": "never", "start_time": "19:00", "duration": 45},
]}


def slug(name):
    return name.lower().replace(" ", "_")


def write(user_dir, rel, payload):
    path = os.path.join(user_dir, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def placed_names(schedule):
    names = []
    for block in schedule.get("conceptual_schedule", {}).get("conceptual_blocks", []):
        names.append(block.get("name"))
        names.extend(child.get("name") for child in (block.get("children") or []))
    return names


history = {name: [] for name in CHORES}
per_day_counts = []
print(f"All 26 wizard chores set up on {SETUP:%a %d %b %Y}. Skipped on purpose: "
      "Laundry on 18 and 19 Nov, Vacuum Floors 16-22 Nov.")
for day in DAYS:
    with temporary_kairos_user_fixture() as fixture:
        user_dir = fixture["user_dir"]
        for name in os.listdir(os.path.join(user_dir, "days")):
            os.remove(os.path.join(user_dir, "days", name))
        write(user_dir, "days/chore_day.yml", DAY_TEMPLATE)
        for name, (frequency, minutes) in CHORES.items():
            write(user_dir, f"habits/{slug(name)}.yml", {
                "name": name, "type": "habit", "chore": True, "frequency": frequency, "duration": minutes,
                "created": SETUP.isoformat(), "completion_dates": list(history[name]),
            })
        with contextlib.redirect_stdout(io.StringIO()):
            result = KairosV2Scheduler({"now": datetime(day.year, day.month, day.day, 8, 0)}).generate_schedule(day)
    schedule = result.get("schedule", {})
    placed = set(placed_names(schedule))
    states = {row["name"]: row for row in (schedule.get("recurring") or {}).get("items", [])}
    periodic = sorted(n for n in placed if n in CHORES and CHORES[n][0] != "daily")
    daily = sorted(n for n in placed if n in CHORES and CHORES[n][0] == "daily")
    for name in placed:
        if name in CHORES and name not in SKIPS.get(day, set()):
            history[name].append(day.isoformat())
    shown = []
    for name in periodic:
        row = states.get(name) or {}
        tag = row.get("state", "")
        if name in SKIPS.get(day, set()):
            tag += ", skipped"
        shown.append(f"{name} ({CHORES[name][0]}, {tag})")
    minutes = sum(CHORES[n][1] for n in periodic)
    per_day_counts.append(len(periodic))
    print(f"{day:%a %d %b}: {len(daily)} daily; {len(periodic)} other ({minutes} min): " + ("; ".join(shown) or "-"))

print()
print(f"Most once-per-period chores on one day: {max(per_day_counts)}; days with none: {per_day_counts.count(0)} of {len(DAYS)}.")
for name, (frequency, _) in CHORES.items():
    if frequency == "weekly":
        weeks = sorted({date.fromisoformat(d).isocalendar()[1] for d in history[name]})
        print(f"  {name}: done in ISO weeks {weeks}")
for name, (frequency, _) in CHORES.items():
    if frequency in ("monthly", "quarterly", "yearly"):
        print(f"  {name} ({frequency}): done on {', '.join(history[name]) or 'not in these four weeks'}")
