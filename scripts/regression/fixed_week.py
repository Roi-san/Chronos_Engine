import sys, os, io, contextlib, yaml
root = sys.argv[1]; sys.path[:0] = [root, os.path.join(root, "tests")]; os.chdir(root)
from datetime import datetime, timedelta
from chronos_fixture import temporary_kairos_user_fixture
from modules.scheduler.kairos_v2 import KairosV2Scheduler
def w(user, rel, data):
    p = os.path.join(user, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f: yaml.safe_dump(data, f, sort_keys=False)
rows = [{"Name": n, "Rank": r} for r, n in enumerate(["Health","Place","Energy","Mind State","Focus","Emotion","Vibe"], 1)]
LIFE = {
 "settings/status_settings.yml": {"Status_Settings": rows},
 "settings/health_settings.yml": {"Health_Settings": {"Excellent": {"value": 1}, "Good": {"value": 2}, "Fair": {"value": 3}, "Poor": {"value": 4}, "Critical": {"value": 5}}},
 "settings/energy_settings.yml": {"Energy_Settings": {"High": {"value": 1}, "Medium": {"value": 2}, "Low": {"value": 3}, "Exhausted": {"value": 4}}},
 "settings/focus_settings.yml": {"Focus_Settings": {"Laser": {"value": 1}, "Good": {"value": 2}, "Scattered": {"value": 3}, "Absent": {"value": 4}}},
 "settings/scheduling_priorities.yml": {"Scheduling_Priorities": [{"Name": "Priority Property", "Order": 1, "Rank": 4}, {"Name": "Goal Alignment", "Order": 2, "Rank": 5}, {"Name": "Commitment Pressure", "Order": 3, "Rank": 5}, {"Name": "Due Date", "Order": 4, "Rank": 4}, {"Name": "Deadline", "Order": 5, "Rank": 5}]},
 "days/rich.yml": {"name": "Rich Day", "type": "day", "children": [
    {"name": "Sleep", "type": "timeblock", "sleep": True, "reschedule": "never", "start_time": "23:00", "duration": 480},
    {"name": "Deep work", "type": "task", "start_time": "09:00", "duration": 120, "category": "work", "status_requirements": {"focus": ["laser", "good"]}},
    {"name": "Gym", "type": "habit", "start_time": "18:00", "duration": 60}]},
 "habits/gym.yml": {"name": "Gym", "type": "habit", "duration": "60m", "status_requirements": {"health": ["excellent","good"], "energy": ["high"]}},
 "habits/mob.yml": {"name": "Mobility", "type": "habit", "duration": "20m", "mini_of": "Gym"},
 "tasks/post.yml": {"name": "Write launch post", "type": "task", "duration": "45m", "category": "work", "goal": "Ship it"},
 "goals/g.yml": {"name": "Ship it", "type": "goal", "priority": "high", "due_date": "2026-04-18"},
 "habits/read.yml": {"name": "Read 30 pages", "type": "habit", "duration": "30m", "frequency": "monday"},
 "commitments/c.yml": {"name": "Read 4x a week", "type": "commitment", "status": "active", "rule": {"kind": "frequency", "times": 4, "period": "week"}, "targets": [{"type": "habit", "name": "Read 30 pages"}]},
 "tasks/inbox.yml": {"name": "Inbox sweep", "type": "task", "duration": "15m", "due_date": "2026-04-19", "status_requirements": {"energy": "low"}},
 "tasks/bank.yml": {"name": "Call the bank", "type": "task", "duration": "20m", "due_date": "2026-04-20"},
}
STATUS = [{"health":"good","energy":"high","focus":"laser"}, {"health":"good","energy":"medium","focus":"good"},
          {"health":"good","energy":"low","focus":"scattered"}, {"health":"poor","energy":"low","focus":"scattered"},
          {"health":"fair","energy":"exhausted","focus":"absent"}, {"health":"excellent","energy":"high","focus":"laser"}, None]
def walk(blocks, out, d=0):
    for b in blocks or []:
        out.append("  "*d + f"{b.get('start_time')}-{b.get('end_time')} {b.get('name')}"); walk(b.get("children"), out, d+1)
start = datetime(2026, 4, 13, 6, 0)
for i, status in enumerate(STATUS):
    now = start + timedelta(days=i)
    with temporary_kairos_user_fixture() as fx:
        user = fx["user_dir"]
        for n in os.listdir(os.path.join(user, "days")): os.remove(os.path.join(user, "days", n))
        for rel, data in LIFE.items(): w(user, rel, data)
        w(user, "profile/current_status.yml", status or {})
        with contextlib.redirect_stdout(io.StringIO()):
            r = KairosV2Scheduler({"now": now}).generate_schedule(now.date())
    s = r["schedule"]; sd = s.get("status_scale_down") or {}
    out = [f"=== {now.date()} {now.strftime('%a')} status={status}"]
    if sd:
        out.append("  swapped: " + str([(x['from'], x['to']) for x in sd.get('swapped', [])]))
        out.append("  kept:    " + str([(x['name'], x['kind'], x.get('urgent_because') or x.get('importance')) for x in sd.get('kept', [])]))
        out.append("  saved:   " + str([(x['name'], x['strain'], x['importance']) for x in sd.get('saved', [])]))
    walk(s.get("conceptual_schedule", {}).get("conceptual_blocks"), out)
    print("\n".join(out))
