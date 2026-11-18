"""
List the habit files in an export and the fields recurring items depend on
(roadmap step 1c). Pair with chore_setup_check.js: it shows what the Chore Setup
wizard really wrote, next to what it said it did.
Usage: python scripts/regression/chore_files.py <export>
"""
import os
import sys

import yaml

root = sys.argv[1]
folder = os.path.join(root, "user", "habits")
names = sorted(n for n in os.listdir(folder) if n.endswith(".yml")) if os.path.isdir(folder) else []
print(f"{len(names)} habit file(s) in {folder}")
for name in names:
    with open(os.path.join(folder, name), "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    data = {str(k).lower(): v for k, v in data.items()} if isinstance(data, dict) else {}
    fields = {key: data.get(key) for key in ("name", "frequency", "day", "duration", "chore", "created") if key in data}
    if "data" in data:
        fields["data (nested!)"] = str(data["data"])[:80]
    print(f"  {name}: {fields}")
