import sys, os, io, contextlib, yaml
root = sys.argv[1]; sys.path[:0] = [root, os.path.join(root, "tests")]; os.chdir(root)
from datetime import datetime, timedelta
from chronos_fixture import temporary_kairos_user_fixture
from modules.scheduler.kairos_v2 import KairosV2Scheduler
def w(user, rel, data):
    p = os.path.join(user, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f: yaml.safe_dump(data, f, sort_keys=False)
LIFE = {
 "days/rich.yml": {"name": "Rich Day", "type": "day", "children": [
    {"name": "Sleep", "type": "timeblock", "sleep": True, "reschedule": "never", "start_time": "23:00", "duration": 480},
    {"name": "Dinner", "type": "timeblock", "reschedule": "never", "start_time": "19:00", "duration": 45},
    {"name": "Morning Routine", "type": "routine", "ideal_start_time": "07:30", "duration": "30m"},
    {"name": "Admin", "window": True, "start": "09:00", "end": "11:00", "filters": {"tags": ["admin"]}},
    {"name": "Focus", "window": True, "start": "13:00", "end": "16:00", "filters": {"category": "work"}},
 ]},
 "habits/stretch.yml": {"name": "Stretch", "type": "habit", "duration": "10m", "frequency": "daily"},
 "habits/gym.yml": {"name": "Gym session", "type": "habit", "duration": "60m", "frequency": "monday", "status_requirements": {"energy": ["high"]}},
 "habits/mob.yml": {"name": "Home mobility", "type": "habit", "duration": "20m", "mini_of": "Gym session"},
 "habits/read.yml": {"name": "Read", "type": "habit", "duration": "30m", "frequency": "weekly"},
 "habits/doom.yml": {"name": "Doomscroll", "type": "habit", "duration": "30m", "frequency": "daily", "polarity": "bad"},
 "commitments/c.yml": {"name": "Three workouts", "type": "commitment", "status": "active",
     "rule": {"kind": "frequency", "times": 3, "period": "week"},
     "targets": [{"type": "habit", "name": "Gym session"}, {"type": "task", "name": "Morning run"}]},
 "goals/g.yml": {"name": "Ship it", "type": "goal", "priority": "high", "due_date": "2026-04-18"},
 "tasks/bank.yml": {"name": "Call the bank", "type": "task", "duration": "20m", "tags": ["admin"], "due_date": "2026-04-14"},
 "tasks/landlord.yml": {"name": "Reply to landlord", "type": "task", "duration": "15m", "tags": ["admin"], "deadline": "2026-04-17"},
 "tasks/report.yml": {"name": "Write report", "type": "task", "duration": "90m", "category": "work", "priority": "high", "due_date": "2026-04-16"},
 "tasks/post.yml": {"name": "Write launch post", "type": "task", "duration": "45m", "category": "work", "goal": "Ship it"},
 "tasks/rent.yml": {"name": "Pay rent", "type": "task", "duration": "30m", "tags": ["admin"], "due_date": "2026-04-13", "status": "completed", "completion_dates": ["2026-04-13"]},
 "tasks/run.yml": {"name": "Morning run", "type": "task", "duration": "30m", "status": "completed"},
 "tasks/dentist.yml": {"name": "Book dentist", "type": "task", "duration": "10m", "tags": ["admin"], "due_date": "2026-04-15", "status": "skipped"},
 "tasks/old.yml": {"name": "Cancelled trip", "type": "task", "duration": "60m", "due_date": "2026-04-15", "status": "cancelled"},
 "tasks/plants.yml": {"name": "Water plants", "type": "task", "duration": "5m", "frequency": "monday, thursday", "status": "completed"},
 "profile/current_status.yml": {"energy": "low", "health": "good"},
}
def walk(blocks, out, d=0):
    for b in blocks or []:
        out.append("  "*d + f"{b.get('start_time')}-{b.get('end_time')} {b.get('name')}")
        walk(b.get("children"), out, d+1)
start = datetime(2026, 4, 13, 6, 0)
for i in range(7):
    now = start + timedelta(days=i)
    with temporary_kairos_user_fixture() as fx:
        user = fx["user_dir"]
        for n in os.listdir(os.path.join(user, "days")): os.remove(os.path.join(user, "days", n))
        for rel, data in LIFE.items(): w(user, rel, data)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            r = KairosV2Scheduler({"now": now}).generate_schedule(now.date())
    s = r["schedule"]
    out = [f"=== {now.date()} {now.strftime('%a')} template={(s.get('day_template') or {}).get('name')}",
           "universe: " + ", ".join(sorted(c['name'] for c in s.get('candidate_universe',{}).get('candidates',[])))]
    walk(s.get("conceptual_schedule", {}).get("conceptual_blocks"), out)
    print("\n".join(out))
