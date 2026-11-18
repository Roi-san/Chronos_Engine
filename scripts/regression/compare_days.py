"""Compare two plan dumps day by day: same items planned? which times moved? any overlaps?

Usage: python compare_days.py <before.txt> <after.txt>
A dump has "=== <date> ..." headers and lines like "  06:00-06:10 Stretch Break".
"""
import re
import sys

LINE = re.compile(r"^\s*(\d{2}):(\d{2})-(\d{2}):(\d{2})\s+(.+?)\s*$")


def parse(path):
    days, current = {}, None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            if raw.startswith("==="):
                current = raw.split()[1]
                days[current] = []
                continue
            match = LINE.match(raw)
            if match and current:
                h1, m1, h2, m2, name = match.groups()
                if name.startswith("Gap Fill") or name.startswith("Quick Wins"):
                    continue
                days[current].append((name, int(h1) * 60 + int(m1), int(h2) * 60 + int(m2), raw.startswith("  ")))
    return days


before, after = parse(sys.argv[1]), parse(sys.argv[2])
moved_total = 0
for day in before:
    b_names = sorted(row[0] for row in before[day])
    a_names = sorted(row[0] for row in after.get(day, []))
    same = b_names == a_names
    b_times = {row[0]: (row[1], row[2]) for row in before[day]}
    moved = [(name, b_times.get(name), (s, e)) for name, s, e, _ in after.get(day, []) if b_times.get(name) != (s, e)]
    moved_total += len(moved)
    # Overlaps among leaf items (indented lines are children; top-level blocks are containers or fixed).
    leaves = sorted((s, e, n) for n, s, e, child in after.get(day, []) if child)
    overlaps = [(a[2], b[2]) for a, b in zip(leaves, leaves[1:]) if b[0] < a[1]]
    print(f"{day}: same items={same} moved={len(moved)} overlaps={overlaps or 'none'}")
    for name, old, new in moved:
        fmt = lambda t: f"{t[0] // 60:02d}:{t[0] % 60:02d}-{t[1] // 60:02d}:{t[1] % 60:02d}" if t else "-"  # noqa: E731
        print(f"    {name}: {fmt(old)} -> {fmt(new)}")
print("total moved:", moved_total)
