"""Print what Home would show: utilities/dashboard/home_api._today() on an export.

Usage: python e2e_home.py <export_root>
"""
import json
import os
import sys

root = os.path.abspath(sys.argv[1])
os.chdir(root)
sys.path[:0] = [root, os.path.join(root, "utilities", "dashboard")]
import home_api  # noqa: E402
import yaml  # noqa: E402

today = home_api._today()
print("schedule file exists:", today.get("exists"))
for b in today.get("blocks", []):
    print(f"  {b['start']}-{b['end']}  {b['name']}  [{b.get('kind') or b.get('type')}]")
shadow = os.path.join(root, "user", "schedules", f"schedule_{today['date']}_kairos_v2_shadow.yml")
if os.path.exists(shadow):
    with open(shadow, encoding="utf-8") as fh:
        meta = (yaml.safe_load(fh) or {}).get("schedule", {})
    print("day_budget:", json.dumps(meta.get("day_budget"), sort_keys=True))
    print("sleep state:", (meta.get("sleep_commitment") or {}).get("current_day_state"))
