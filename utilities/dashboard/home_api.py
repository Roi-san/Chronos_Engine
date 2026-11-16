"""
Home view API.

One read-only JSON endpoint (`GET /api/home/summary`) that gives the Home view
everything it needs in a single round trip: who the pilot is, how they are
(status), what today looks like, and what their life currently contains.

It only reads. Everything the Home view changes goes through the existing
endpoints (`/api/item`, `/api/status/update`, `/api/cli`), so there is one
write path for the whole dashboard.
"""
import os
import re
from datetime import datetime

import yaml

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
USER_DIR = os.path.join(ROOT_DIR, "user")
SETTINGS_DIR = os.path.join(USER_DIR, "settings")

# The areas of a life Chronos models, in the order the Home view shows them.
LIFE_TYPES = [
    "goal", "milestone", "project", "commitment", "habit",
    "routine", "subroutine", "microroutine", "day", "week",
    "task", "appointment", "reminder", "alarm", "note",
]

ITEM_FIELDS = (
    "status", "priority", "category", "duration", "due_date", "deadline",
    "frequency", "tags", "description", "polarity", "chore", "time", "date",
)


def _read_yaml(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except Exception:
        return None


def _settings_file(*names):
    """Settings files exist in both lower and Title case across versions."""
    wanted = {n.lower() for n in names}
    try:
        for entry in os.listdir(SETTINGS_DIR):
            if entry.lower() in wanted:
                return os.path.join(SETTINGS_DIR, entry)
    except OSError:
        pass
    return None


def _hm(value):
    match = re.search(r"(\d{1,2}):(\d{2})", str(value or ""))
    if not match:
        return None
    return f"{min(23, int(match.group(1))):02d}:{min(59, int(match.group(2))):02d}"


def _profile():
    data = _read_yaml(os.path.join(USER_DIR, "profile", "profile.yml")) or {}
    return {"nickname": str(data.get("nickname") or "").strip()}


def _status():
    """Current status plus the choices for each dimension (energy, health, ...)."""
    current = {}
    try:
        from modules.scheduler import status_current_path
        raw = _read_yaml(status_current_path()) or {}
        if isinstance(raw, dict):
            current = {str(k).lower(): str(v) for k, v in raw.items() if v is not None}
    except Exception:
        pass

    dimensions = []
    cfg = _read_yaml(_settings_file("status_settings.yml") or "") or {}
    rows = cfg.get("Status_Settings") if isinstance(cfg, dict) else None
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not row.get("Name"):
            continue
        name = str(row["Name"])
        slug = name.strip().lower().replace(" ", "_")
        options = []
        data = _read_yaml(_settings_file(f"{slug}_settings.yml") or "") or {}
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict) and str(key).lower().endswith("_settings"):
                    ranked = sorted(
                        value.items(),
                        key=lambda kv: (kv[1].get("value", 99) if isinstance(kv[1], dict) else 99),
                    )
                    options = [
                        {
                            "name": str(opt),
                            "description": str((meta or {}).get("description") or "") if isinstance(meta, dict) else "",
                        }
                        for opt, meta in ranked
                    ]
                    break
        dimensions.append({
            "name": name,
            "key": slug,
            "description": str(row.get("Description") or ""),
            "options": options,
            "current": current.get(slug) or current.get(name.lower()) or "",
        })
    return {"current": current, "dimensions": dimensions}


def _today():
    """Today's generated schedule, flattened, with what has been done so far."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    out = {"date": date_str, "exists": False, "blocks": [], "completions": {}}
    closed_entries = []

    comp = _read_yaml(os.path.join(USER_DIR, "schedules", "completions", f"{date_str}.yml")) or {}
    entries = comp.get("entries") if isinstance(comp, dict) else None
    if isinstance(entries, dict):
        for key, value in entries.items():
            entry = value if isinstance(value, dict) else {"status": value}
            name = entry.get("name") or (str(key).split("@", 1)[0] if "@" in str(key) else key)
            status = str(entry.get("status") or "").strip().lower()
            if name and status:
                out["completions"][str(name).strip().lower()] = status
                closed_entries.append({
                    "name": str(name),
                    "status": status,
                    "start": _hm(entry.get("scheduled_start") or entry.get("actual_start")),
                    "end": _hm(entry.get("scheduled_end") or entry.get("actual_end")),
                })

    try:
        from modules.scheduler import schedule_path_for_date, load_schedule_payload_for_date
        path = schedule_path_for_date(date_str)
        if not os.path.exists(path):
            return out
        payload = load_schedule_payload_for_date(date_str, path=path)
    except Exception as exc:
        out["error"] = str(exc)
        return out

    out["exists"] = True

    def walk(items, depth, group=""):
        for item in items or []:
            if not isinstance(item, dict):
                continue
            original = item.get("original_item_data") if isinstance(item.get("original_item_data"), dict) else {}
            name = item.get("name") or original.get("name") or ""
            start = _hm(item.get("start_time") or original.get("start_time") or item.get("ideal_start_time"))
            end = _hm(item.get("end_time") or item.get("ideal_end_time"))
            children = item.get("children") or item.get("items") or []
            kind = str(item.get("kind") or "").lower()
            # A block that holds other scheduled blocks (a window, a gap fill) is a
            # container: the pilot acts on what is inside it, not on the container.
            container = bool(item.get("window")) or kind in ("window", "gap_fill", "free", "buffer") or any(
                isinstance(child, dict) and _hm(child.get("start_time")) for child in (children if isinstance(children, list) else [])
            )
            if name and start and end:
                reschedule = str(item.get("reschedule") or original.get("reschedule") or "").lower()
                out["blocks"].append({
                    "name": str(name),
                    "type": str(item.get("type") or original.get("type") or "").lower(),
                    "start": start,
                    "end": end,
                    "depth": depth,
                    "anchored": bool(item.get("anchored")) or reschedule == "never",
                    "window": bool(item.get("window")),
                    "kind": kind,
                    "container": container,
                    # Name of the enclosing window, when that window is worth showing.
                    "group": group,
                    "status": out["completions"].get(str(name).strip().lower(), ""),
                })
            if isinstance(children, list):
                shown_group = str(name) if container and kind != "gap_fill" else ""
                walk(children, depth + 1, shown_group)

    if isinstance(payload, list):
        walk(payload, 0)
    elif isinstance(payload, dict):
        walk(payload.get("items") or payload.get("children") or [], 0)
    # A re-plan only lays out what is still to do, so blocks finished or skipped
    # earlier drop out of the schedule. Keep them visible as part of today.
    present = {block["name"].strip().lower() for block in out["blocks"]}
    for entry in closed_entries:
        if entry["name"].strip().lower() in present or not entry["start"] or not entry["end"]:
            continue
        out["blocks"].append({
            "name": entry["name"], "type": "", "start": entry["start"], "end": entry["end"],
            "depth": 0, "anchored": False, "window": False, "kind": "closed",
            "container": False, "group": "", "status": entry["status"],
        })
    # Stable sort: keeps each window's contents directly under its heading.
    out["blocks"].sort(key=lambda b: b["start"])
    return out


def _life():
    """Every item the pilot has, grouped by type, trimmed to what Home displays."""
    from modules.item_manager import list_all_items

    life = {}
    for item_type in LIFE_TYPES:
        rows = []
        try:
            items = list_all_items(item_type) or []
        except Exception:
            items = []
        for data in items:
            if not isinstance(data, dict):
                continue
            lowered = {str(k).lower(): v for k, v in data.items()}
            name = str(lowered.get("name") or "").strip()
            if not name:
                continue
            row = {"name": name, "type": item_type}
            for field in ITEM_FIELDS:
                value = lowered.get(field)
                if value not in (None, "", [], {}):
                    row[field] = value if isinstance(value, (str, int, float, bool, list)) else str(value)
            children = lowered.get("children")
            sequence = lowered.get("sequence")
            row["children"] = (len(children) if isinstance(children, list) else 0) + (
                len(sequence) if isinstance(sequence, list) else 0
            )
            rows.append(row)
        rows.sort(key=lambda r: r["name"].lower())
        life[item_type] = rows
    return life


def _alpha_gate():
    """Gate settings plus the item types the active release profile refuses to create."""
    try:
        from modules import alpha_gate
        snapshot = dict(alpha_gate.settings_snapshot())
        snapshot["disabled_item_types"] = [t for t in LIFE_TYPES if alpha_gate.is_item_type_disabled(t)]
        return snapshot
    except Exception:
        return {}


def build_summary():
    life = _life()
    return {
        "ok": True,
        "now": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "profile": _profile(),
        "status": _status(),
        "today": _today(),
        "life": life,
        "counts": {key: len(rows) for key, rows in life.items()},
        "alpha_gate": _alpha_gate(),
    }


def handle_get(handler, parsed):
    """Returns True when the request was handled."""
    if parsed.path == "/api/home/summary":
        try:
            handler._write_json(200, build_summary())
        except Exception as exc:
            handler._write_json(500, {"ok": False, "error": f"Home summary failed: {exc}"})
        return True
    return False
