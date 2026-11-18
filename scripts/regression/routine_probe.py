"""How does Kairos v2 place routines with and without their own length?"""
import os, sys
EXPORT = sys.argv[1]
for p in (EXPORT, os.path.join(EXPORT, "tests")):
    sys.path.insert(0, p)
os.chdir(EXPORT)
from test_kairos_v2_gaps_and_breathing_room import _result, at

def steps(with_lengths=True):
    def s(name, typ, minutes):
        node = {"name": name, "type": typ}
        if with_lengths:
            node["duration"] = minutes
        return node
    return [s("Brush teeth", "habit", 5), s("Shower", "habit", 15), s("Make breakfast", "task", 10)]

LUNCH = {"name": "Lunch", "type": "timeblock", "reschedule": "never", "start_time": "12:00", "end_time": "12:30", "duration": 30}
cases = {
    "A routine WITHOUT its own length, steps 5+15+10": {"name": "Morning Routine", "type": "routine", "children": steps(True)},
    "B routine WITH its own length (20m), steps 5+15+10": {"name": "Morning Routine", "type": "routine", "duration": 20, "children": steps(True)},
    "C routine without length, steps without lengths": {"name": "Morning Routine", "type": "routine", "children": steps(False)},
    "D routine from the library (no length), steps 5+15+10": None,
}
for label, node in cases.items():
    files = {}
    children = [LUNCH]
    if node is None:
        files = {"routines/morning.yml": {"name": "Morning Routine", "type": "routine", "frequency": "daily", "children": steps(True)}}
    else:
        children.append(node)
    result = _result(children, files, at(8, 0))
    sched = result.get("schedule", {})
    print(f"--- {label}")
    for b in sched.get("conceptual_schedule", {}).get("conceptual_blocks", []):
        kids = b.get("children") or []
        print(f"  {b.get('start_time')}-{b.get('end_time')} {b.get('name')} [{b.get('kind')}]" + ("" if not kids else ""))
        for c in kids:
            print(f"      {c.get('start_time')}-{c.get('end_time')} {c.get('name')} ({c.get('type')})")
