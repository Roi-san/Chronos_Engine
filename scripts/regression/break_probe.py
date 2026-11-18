"""Does an authored break/buffer timeblock reach the timer as a break (is_buffer)?"""
import os, sys
EXPORT = sys.argv[1]
for p in (EXPORT, os.path.join(EXPORT, "tests")):
    sys.path.insert(0, p)
os.chdir(EXPORT)
from test_kairos_v2_gaps_and_breathing_room import _result, at
from modules.scheduler.runtime import build_day_runtime_payload, build_schedule_plan

children = [
    {"name": "Break", "type": "timeblock", "subtype": "break", "start_time": "15:00", "end_time": "15:15", "duration": 15},
    {"name": "Buffer", "type": "timeblock", "subtype": "buffer", "start_time": "16:00", "end_time": "16:20", "duration": 20},
    {"name": "Work", "type": "timeblock", "start_time": "17:00", "end_time": "18:00", "duration": 60, "reschedule": "never"},
]
now = at(14, 0)
result = _result(children, {}, now)
sched = result.get("schedule", {})
print("conceptual blocks:")
for b in sched.get("conceptual_schedule", {}).get("conceptual_blocks", []):
    print(f"  {b.get('name')!r:12} kind={b.get('kind')!r:14} type={b.get('type')!r:12} subtype={b.get('subtype')!r}")
print("execution units:")
for u in sched.get("timer_handoff", {}).get("execution_units", []):
    print(f"  {u.get('name')!r:12} kind={u.get('kind')!r:16} type={u.get('type')!r}")
payload = build_day_runtime_payload(now.date(), result)
plan = build_schedule_plan(payload, now_dt=now, date_key=now.date().isoformat())
print("timer plan blocks:")
for b in plan["blocks"]:
    print(f"  {b['name']!r:12} is_buffer={b['is_buffer']!s:5} is_break={b['is_break']!s:5} type={b['type']!r}")
