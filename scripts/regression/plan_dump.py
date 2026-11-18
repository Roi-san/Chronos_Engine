import sys, os, io, contextlib
root = sys.argv[1]; sys.path[:0] = [root, os.path.join(root, "tests")]; os.chdir(root)
from datetime import datetime, timedelta
from chronos_fixture import temporary_kairos_user_fixture
from modules.scheduler.kairos_v2 import KairosV2Scheduler
def walk(blocks, out, d=0):
    for b in blocks or []:
        out.append("  "*d + f"{b.get('start_time')}-{b.get('end_time')} {b.get('name')} [{b.get('kind') or b.get('type')}]")
        walk(b.get("children"), out, d+1)
start = datetime(2026, 4, 13, 7, 0)
for i in range(7):
    now = start + timedelta(days=i)
    with temporary_kairos_user_fixture():
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            r = KairosV2Scheduler({"now": now}).generate_schedule(now.date())
    s = r["schedule"]; out = [f"=== {now.date()} template={(s.get('day_template') or {}).get('name')} universe={s.get('candidate_universe',{}).get('count')}"]
    walk(s.get("conceptual_schedule", {}).get("conceptual_blocks"), out)
    print("\n".join(out))
