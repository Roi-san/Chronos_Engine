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
    "goal", "mini_of", "mini_variant",
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


# -- what today's status did to the plan ---------------------------------------
# Kairos writes `schedule.status_scale_down` (modules/scheduler/kairos_v2.py,
# docs/scheduling/status_scale_down_design.md): lighter versions swapped in,
# items kept although today falls short, and items saved for a better day.
# Home turns that record into plain sentences here, so the wording is tested
# (tests/test_home_api_status_effects.py) and the view only displays it.

_URGENT_TEXT = {
    "deadline_today": "its deadline is today",
    "deadline_overdue": "its deadline has passed",
    "due_date_today": "it is due today",
    "due_date_overdue": "it is overdue",
    "commitment_last_chance": "it is the last chance to keep its commitment",
    "commitment_behind": "its commitment is behind",
}

_IMPORTANT_TEXT = {
    "commitment": "its commitment matters more than the strain",
    "goal": "its goal matters more than the strain",
    "priority": "its priority matters more than the strain",
    # Recurring pressure (decision D2): a weekly to yearly item whose period is running out.
    "recurring": "keeping its rhythm matters more than the strain",
}


def _label(value):
    return str(value or "").strip().replace("_", " ")


def _shortfall_text(short_dimensions):
    """'energy is low (needs high or medium)'; several joined with 'and'."""
    parts = []
    for row in short_dimensions or []:
        if not isinstance(row, dict) or not row.get("dimension"):
            continue
        accepts = [_label(v) for v in (row.get("accepts") or []) if _label(v)]
        needs = f" (needs {' or '.join(accepts)})" if accepts else ""
        parts.append(f"{_label(row['dimension'])} is {_label(row.get('today')) or 'unknown'}{needs}")
    return " and ".join(parts)


def _kept_reason(row):
    kind = str(row.get("kind") or "")
    if kind == "within_grace":
        return "it is only a little short"
    if kind == "urgent":
        return _URGENT_TEXT.get(str(row.get("urgent_because") or ""), "it is urgent")
    if kind == "important":
        sources = [s for s in (row.get("importance_sources") or []) if isinstance(s, dict) and s.get("source")]
        if sources:
            top = max(sources, key=lambda s: float(s.get("value") or 0.0))
            return _IMPORTANT_TEXT.get(str(top["source"]), "it matters more than the strain")
        return "it matters more than the strain"
    return ""


def _identity_type(identity):
    text = str(identity or "")
    return text.split(":", 1)[0].strip().lower() if ":" in text else ""


def status_effects(record):
    """
    Plain-language view of `schedule.status_scale_down` for Home.

    Returns:
      saved: [{name, type, fixed_slot, text}] in plan order. `type` feeds Add back
             (`today inject "<name>" type:<type>`).
      kept:  {lowercase name: sentence} for blocks kept although today falls short.
    Missing or malformed input gives empty lists, never an error.
    """
    out = {"saved": [], "kept": {}}
    if not isinstance(record, dict):
        return out
    seen = set()
    rows = lambda key: record.get(key) if isinstance(record.get(key), list) else []
    for row in rows("saved"):
        if not isinstance(row, dict) or not str(row.get("name") or "").strip():
            continue
        name = str(row["name"]).strip()
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        shortfall = _shortfall_text(row.get("short_dimensions"))
        out["saved"].append({
            "name": name,
            "type": _identity_type(row.get("identity")) or "task",
            "fixed_slot": str(row.get("fixed_slot") or ""),
            "text": f"Today {shortfall}." if shortfall else "Today does not fit it.",
        })
    for row in rows("kept"):
        if not isinstance(row, dict) or not str(row.get("name") or "").strip():
            continue
        shortfall = _shortfall_text(row.get("short_dimensions"))
        reason = _kept_reason(row)
        text = "Kept although today does not quite fit it"
        if shortfall:
            text = f"Kept although {shortfall}"
        out["kept"][str(row["name"]).strip().lower()] = f"{text}: {reason}." if reason else f"{text}."
    return out


# -- lengths Kairos assumed --------------------------------------------------------
# Kairos records `schedule.assumed_lengths` (decision D1,
# docs/scheduling/item_lengths.md): items planned with the default length because
# they have none, and routines planned for the total of their steps.

def length_notes(record):
    """
    Plain-language view of `schedule.assumed_lengths` for Home.

    Returns:
      notes: {lowercase name: sentence} for every block whose length was assumed.
      unset: lowercase names planned with the default length (Home tags them).
    Missing or malformed input gives empty results, never an error.
    """
    out = {"notes": {}, "unset": []}
    if not isinstance(record, list):
        return out
    for row in record:
        if not isinstance(row, dict) or not str(row.get("name") or "").strip():
            continue
        key = str(row["name"]).strip().lower()
        try:
            minutes = int(row.get("minutes") or 0)
        except (TypeError, ValueError):
            minutes = 0
        if minutes <= 0:
            continue
        source = str(row.get("source") or "")
        if source == "default":
            out["notes"][key] = f"No length set, so Chronos planned {minutes} min. Set its real length in Manage."
            if key not in out["unset"]:
                out["unset"].append(key)
        elif source == "steps":
            out["notes"][key] = f"Planned for {minutes} min, the total of its steps."
    return out


def day_template_line(meta):
    """
    Which day template today's plan used and why, for Home (decision D6,
    2026-11-19): {"name", "why"}, or None for a plan without that record.
    """
    choice = meta.get("day_template_choice") if isinstance(meta, dict) else None
    if not isinstance(choice, dict) or "why" not in choice:
        return None
    return {"name": choice.get("name"), "why": str(choice.get("why") or "")}


def plan_notes(meta):
    """
    Things Kairos did that would otherwise only be in the schedule file: sleep
    found by a block's name (D5), an own time that could not be kept (D7), and
    files it could not read (issue 31).
    """
    notes = []
    if not isinstance(meta, dict):
        return notes
    sleep = meta.get("sleep_blocks")
    if isinstance(sleep, dict) and sleep.get("by_name") and sleep.get("note"):
        notes.append(str(sleep["note"]))
    # An item's own time is a wish (D7): when it could not be kept, say why.
    for row in meta.get("wished_times") or []:
        if isinstance(row, dict) and not row.get("placed") and row.get("name"):
            notes.append(f"{row['name']} wanted {row.get('wished')}, but {row.get('why')}, so Chronos planned it in free time instead.")
    for row in meta.get("unreadable_files") or []:
        if isinstance(row, dict) and row.get("file"):
            notes.append(f"Skipped {row['file']}: Chronos could not read it ({row.get('error') or 'unknown error'}). Fix or remove the file.")
    return notes


def _default_item_minutes():
    """The length Kairos gives an item without one (scheduling_settings.yml), as Home shows it."""
    data = _read_yaml(_settings_file("scheduling_settings.yml") or "") or {}
    try:
        value = int(data.get("default_duration_minutes") or 0) if isinstance(data, dict) else 0
    except (TypeError, ValueError):
        value = 0
    return value if value > 0 else 30


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
    out = {
        "date": date_str, "exists": False, "blocks": [], "completions": {},
        "status_effects": status_effects(None), "length_notes": length_notes(None),
    }
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
    meta = payload.get("schedule") if isinstance(payload, dict) else None
    try:
        filtered = meta.get("reality_filtered_candidates") if isinstance(meta, dict) else None
        out["scaled_down"] = list(filtered.get("scaled_down") or []) if isinstance(filtered, dict) else []
    except Exception:
        out["scaled_down"] = []
    try:
        record = meta.get("status_scale_down") if isinstance(meta, dict) else None
        record = record if isinstance(record, dict) else {}
        # Fixed-slot swaps (step 2) are only in this record, not in `scaled_down`.
        for row in record.get("swapped") or []:
            if isinstance(row, dict) and row.get("to") and row not in out["scaled_down"]:
                out["scaled_down"].append(row)
        out["status_effects"] = status_effects(record)
    except Exception:
        out["status_effects"] = status_effects(None)
    try:
        out["length_notes"] = length_notes(meta.get("assumed_lengths") if isinstance(meta, dict) else None)
    except Exception:
        out["length_notes"] = length_notes(None)
    out["day_template"] = day_template_line(meta)
    out["plan_notes"] = plan_notes(meta)

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
    # Something saved for a better day that is on the plan after all (added back,
    # placed by hand) or already done today no longer needs the Add back button.
    on_today = present | set(out["completions"])
    out["status_effects"]["saved"] = [
        row for row in out["status_effects"]["saved"] if row["name"].strip().lower() not in on_today
    ]
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


def _direction(today):
    """
    Goal, commitment and recurring pressure for today, keyed by item name for
    the Home view. Uses the same module the scheduler does, so Home explains
    what Kairos sees. `state` drives the "last chance" / "at risk" tag; when an
    item has both, the commitment's state wins over the recurring one.
    """
    out = {"by_name": {}, "commitments": [], "goals": [], "scaled_down": {}}
    try:
        from modules.scheduler import direction as Direction
        from modules.scheduler import periods as Periods
        loaded = Direction.load_direction(USER_DIR, Periods.today())
    except Exception as exc:
        out["error"] = str(exc)
        return out
    for identity, signal in (loaded.get("by_identity") or {}).items():
        name = identity.split(":", 1)[1] if ":" in identity else identity
        row = out["by_name"].setdefault(name, {"reasons": [], "state": ""})
        commitment = signal.get("commitment") or {}
        goal = signal.get("goal") or {}
        recurring = signal.get("recurring") or {}
        if commitment.get("reason"):
            row["reasons"].append(commitment["reason"])
            row["state"] = commitment.get("state") or ""
        if goal.get("reason"):
            row["reasons"].append(goal["reason"])
        if recurring.get("reason"):
            row["reasons"].append(recurring["reason"])
            if not row["state"]:
                row["state"] = recurring.get("state") or ""
    out["commitments"] = [
        {key: row.get(key) for key in ("name", "state", "progress", "required", "days_left", "period", "reason")}
        for row in loaded.get("commitments") or []
    ]
    out["goals"] = loaded.get("goals") or []
    # Which blocks on today's plan stand in for a bigger item.
    for swap in (today.get("scaled_down") or []):
        if isinstance(swap, dict) and swap.get("to") and swap.get("from"):
            out["scaled_down"][str(swap["to"]).strip().lower()] = str(swap["from"])
    return out


def build_summary():
    life = _life()
    today = _today()
    direction = _direction(today)
    today.pop("scaled_down", None)
    return {
        "ok": True,
        "now": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "profile": _profile(),
        "status": _status(),
        "today": today,
        "direction": direction,
        "life": life,
        "counts": {key: len(rows) for key, rows in life.items()},
        "alpha_gate": _alpha_gate(),
        "defaults": {"item_minutes": _default_item_minutes()},
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
