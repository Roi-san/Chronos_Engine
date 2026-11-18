import os
import subprocess
from datetime import datetime, timedelta, date
from modules.item_manager import (
    generic_handle_new,
    generic_handle_append,
    generic_handle_delete,
    get_user_dir,
    list_all_items,
    read_item_data,
    write_item_data,
    open_item_in_editor,
)


def _periods():
    """
    The shared day/period helper, modules/scheduler/periods.py (roadmap step 1c,
    docs/scheduling/recurrence_design.md, "Decisions after the proposal", point 8).
    Imported when needed, like `direction` below: loading the scheduler package
    loads Kairos, which plain commitment commands do not need.
    """
    from modules.scheduler import periods as Periods
    return Periods

ITEM_TYPE = "commitment"

def handle_new(name, properties):
    """Create a new commitment using generic handler."""
    generic_handle_new(ITEM_TYPE, name, properties)


def handle_command(command, item_type, item_name, text_to_append, properties):
    """
    Provide the standard item lifecycle for commitments so CLI generic commands work.
    """
    normalized = (command or "").strip().lower()

    if normalized in ("new", "create"):
        generic_handle_new(item_type, item_name, properties)
        return

    if normalized == "append":
        if not text_to_append:
            print("Info: Nothing to append. Provide text after the commitment name.")
            return
        generic_handle_append(item_type, item_name, text_to_append, properties)
        return

    if normalized == "delete":
        generic_handle_delete(item_type, item_name, properties)
        return

    if normalized in ("info", "view", "track"):
        _print_commitment(item_name)
        return

    if normalized in ("set", "update", "edit"):
        _update_properties(item_name, properties)
        return

    if normalized == "open":
        open_item_in_editor(item_type, item_name, None)
        return

    if normalized == "check":
        evaluate_and_trigger()
        return

    print(f"Unsupported command for commitment: {command}")


def _count_in_period(dates: list[str], period: str) -> int:
    """Completions in the current period, counted against today. Kept for other callers."""
    return _count_in_period_on(dates, period, _periods().today())


def _count_in_period_on(dates: list, period: str, today: date) -> int:
    """
    How many of `dates` fall in the period containing `today`, up to `today`.

    Each entry counts, so two completions on one day count twice (per-target
    counts such as "post 10 times a week" rely on it; the scheduler counts days
    instead, issue 28). Since step 1c the period comes from the shared helper,
    so the tracker and the scheduler agree on where a week (Monday to Sunday),
    month, quarter or year starts; before, this function had its own copy and
    counted all-time for quarters and years. An unknown period still counts
    every entry, as before (issue 28).
    """
    Periods = _periods()
    kind = Periods.normalize_period(period)
    if not kind:
        return len(dates or [])
    start, _ = Periods.period_bounds(today, kind)
    count = 0
    for raw in dates or []:
        day = Periods.parse_day(raw)
        if day and start <= day <= today:
            count += 1
    return count


def _period_key(d: date, period: str) -> str:
    """The key `last_met` / `last_violation` store: the same forms as before step 1c."""
    Periods = _periods()
    kind = Periods.normalize_period(period)
    if not kind:
        return d.strftime("%Y-%m-%d")
    return Periods.period_key(d, kind)


def _logged_completions(period: str, today: date) -> dict:
    """
    {lowercase name: days} logged as completed in the daily completion logs
    during the current period (the period containing `today`, up to `today`).

    Start day (the timer) records a completion only in these logs, never in the
    item's `completion_dates` (issue 24), so the tracker reads them as the
    scheduler always did. Empty for an unknown period.
    """
    Periods = _periods()
    kind = Periods.normalize_period(period)
    if not kind:
        return {}
    start, _ = Periods.period_bounds(today, kind)
    try:
        by_date = Periods.completed_names_by_date(get_user_dir(), start, today)
    except Exception:
        return {}
    out: dict = {}
    for day, names in by_date.items():
        for name in names:
            out.setdefault(name, set()).add(day)
    return out

def _normalize_targets(c: dict) -> list[dict]:
    # Canonical: targets
    targets = c.get('targets') if isinstance(c.get('targets'), list) else None
    if not targets and isinstance(c.get('Targets'), list):
        targets = c.get('Targets')
    if targets:
        return [t for t in targets if isinstance(t, dict)]

    # Legacy: associated_items / forbidden_items
    assoc = c.get('associated_items') if isinstance(c.get('associated_items'), list) else []
    forb = c.get('forbidden_items') if isinstance(c.get('forbidden_items'), list) else []
    if assoc:
        return [t for t in assoc if isinstance(t, dict)]
    if forb:
        return [t for t in forb if isinstance(t, dict)]

    # Legacy: frequency.of / never.of / linked_habit
    freq = c.get('frequency') if isinstance(c.get('frequency'), dict) else {}
    never = c.get('never') if isinstance(c.get('never'), dict) else {}
    of = None
    if isinstance(freq, dict):
        of = freq.get('of')
    if not of and isinstance(never, dict):
        of = never.get('of')
    if isinstance(of, dict) and of.get('type') and of.get('name'):
        return [of]
    linked = c.get('linked_habit')
    if isinstance(linked, str) and linked.strip():
        return [{"type": "habit", "name": linked.strip()}]
    return []

def _normalize_rule(c: dict) -> tuple[str, int, str]:
    # Canonical: rule. commitment_defaults.yml writes `Rule: {Kind:, Times:, Period:}`,
    # so read the keys case-insensitively and ignore a rule that was never filled in.
    rule = c.get('rule') if isinstance(c.get('rule'), dict) else c.get('Rule')
    if isinstance(rule, dict) and rule:
        rule = {str(k).lower(): v for k, v in rule.items()}
    else:
        rule = None
    if rule and str(rule.get('kind') or '').strip():
        kind = str(rule.get('kind') or '').lower()
        try:
            times = int(rule.get('times') or 0)
        except (TypeError, ValueError):
            times = 0
        period = str(rule.get('period') or 'week').lower()
        return (kind, times, period)

    # Legacy: frequency / never
    freq = c.get('frequency') if isinstance(c.get('frequency'), dict) else None
    if freq:
        times = int(freq.get('times') or 0)
        period = str(freq.get('period') or 'week').lower()
        return ('frequency', times, period)
    if c.get('never') is True or isinstance(c.get('never'), dict):
        # Default to day for "never" rules to allow recovery
        return ('never', 0, 'day')
    return ('', 0, 'week')

def _target_required_count(target: dict) -> int:
    if not isinstance(target, dict):
        return 1
    raw = target.get('count')
    if raw is None:
        raw = target.get('times')
    if raw is None:
        raw = target.get('required')
    try:
        n = int(raw)
    except Exception:
        n = 1
    return max(1, n)

def _manual_status_for_date(c: dict, today: date) -> str:
    manual_map = c.get('manual_status_by_date') if isinstance(c.get('manual_status_by_date'), dict) else {}
    val = str(manual_map.get(today.strftime('%Y-%m-%d')) or '').strip().lower()
    if val in ('met', 'violation'):
        return val
    return ''

def _get_item_polarity(item_type: str, item_name: str) -> str:
    data = read_item_data(item_type, item_name)
    if not isinstance(data, dict):
        return "good"
    return str(data.get('polarity') or 'good').lower()

def _date_texts(values) -> list:
    """
    Completion dates as YYYY-MM-DD text, duplicates kept. A date written
    without quotes in YAML is read as a date object; the tracker used to drop
    those while the scheduler counted them (step 1c: now both count them).
    """
    out = []
    for value in values or []:
        if isinstance(value, datetime):
            out.append(value.date().isoformat())
        elif isinstance(value, date):
            out.append(value.isoformat())
        elif isinstance(value, str):
            out.append(value)
    return out


def _get_dates_for_target(item_type: str, item_name: str, *, for_never: bool, logged: dict | None = None) -> list[str]:
    data = read_item_data(item_type, item_name)
    if not isinstance(data, dict):
        return []
    if for_never and item_type == 'habit':
        polarity = str(data.get('polarity') or 'good').lower()
        if polarity == 'bad':
            dates = data.get('incident_dates') or []
            return [d for d in dates if isinstance(d, str)]
    dates = _date_texts(data.get('completion_dates'))
    if not for_never:
        names = [str(data.get('name') or item_name).strip().lower()]
        # A scaled-down version of the target (linked through `mini_variant` /
        # `mini_of`) counts too: doing the smaller thing keeps the promise alive.
        # The scheduler makes the same assumption when it swaps one in.
        for mini_type, mini_name in _mini_items_for(data):
            mini = read_item_data(mini_type, mini_name)
            for d in _date_texts(mini.get('completion_dates')) if isinstance(mini, dict) else []:
                if d not in dates:
                    dates.append(d)
            names.append(str(mini_name).strip().lower())
        # A day on which the item or its lighter version is logged as completed
        # (Start day writes only the log, issue 24) but that is missing from the
        # dates above adds one completion. A day in both places counts once.
        if logged:
            have = {d[:10] for d in dates}
            for day in sorted(set().union(*(logged.get(name, set()) for name in names))):
                if day.isoformat() not in have:
                    dates.append(day.isoformat())
                    have.add(day.isoformat())
    return dates

def _mini_items_for(item: dict) -> list[tuple[str, str]]:
    """(type, name) of every authored scaled-down version of `item`."""
    try:
        from modules.scheduler import direction as Direction
    except Exception:
        return []
    library = []
    for item_type in Direction.LINKABLE_DIRS:
        for other in list_all_items(item_type) or []:
            if isinstance(other, dict):
                lowered = {str(k).lower(): v for k, v in other.items()}
                lowered.setdefault('type', item_type)
                library.append(lowered)
    wanted = set(Direction.mini_names_for(item, library))
    return [
        (str(other.get('type')), str(other.get('name')))
        for other in library
        if str(other.get('name') or '').strip().lower() in wanted
    ]

def _normalize_triggers(c: dict) -> dict:
    triggers = c.get('triggers') if isinstance(c.get('triggers'), dict) else {}
    if not triggers:
        return {}
    # Legacy: on_complete -> on_met
    if 'on_complete' in triggers and 'on_met' not in triggers:
        triggers['on_met'] = triggers.get('on_complete')
    # Normalize script actions
    for key in ('on_met', 'on_violation'):
        actions = triggers.get(key) or []
        if not isinstance(actions, list):
            continue
        for action in actions:
            if not isinstance(action, dict):
                continue
            if str(action.get('type') or '').lower() == 'script':
                # Accept path/script/command/name as the script field
                if not action.get('path'):
                    action['path'] = action.get('script') or action.get('command') or action.get('name')
    return triggers

def get_commitment_status(c: dict, today: date | None = None) -> dict:
    # Since step 1c the day given is the one counted against (it used to be the
    # real clock whatever was passed); with no day, the shared helper's today.
    today = today or _periods().today()
    kind, times, period = _normalize_rule(c)
    targets = _normalize_targets(c)
    triggers = _normalize_triggers(c)
    logged = _logged_completions(period, today) if kind == 'frequency' and targets else {}

    progress = 0
    required_total = times
    remaining = max(0, required_total - progress)
    met = False
    violation = False
    target_progress = []
    if kind == 'frequency':
        has_per_target_counts = any(isinstance(it, dict) and it.get('count') is not None for it in targets)
        if targets:
            valid_target_count = 0
            if has_per_target_counts:
                required_total = 0
                all_met = True
                for it in targets:
                    t = str(it.get('type') or '').strip()
                    n = str(it.get('name') or '').strip()
                    if not t or not n:
                        continue
                    valid_target_count += 1
                    req = _target_required_count(it)
                    dates = _get_dates_for_target(t, n, for_never=False, logged=logged)
                    tgt_progress = _count_in_period_on(dates, period, today)
                    progress += tgt_progress
                    required_total += req
                    tgt_remaining = max(0, req - tgt_progress)
                    if tgt_progress < req:
                        all_met = False
                    target_progress.append({
                        "type": t,
                        "name": n,
                        "required": req,
                        "progress": tgt_progress,
                        "remaining": tgt_remaining,
                        "met": tgt_progress >= req,
                    })
                met = bool(valid_target_count > 0 and all_met)
            else:
                for it in targets:
                    t = str(it.get('type') or '').strip()
                    n = str(it.get('name') or '').strip()
                    if not t or not n:
                        continue
                    valid_target_count += 1
                    dates = _get_dates_for_target(t, n, for_never=False, logged=logged)
                    tgt_progress = _count_in_period_on(dates, period, today)
                    progress += tgt_progress
                    target_progress.append({
                        "type": t,
                        "name": n,
                        "required": 1,
                        "progress": tgt_progress,
                        "remaining": max(0, 1 - tgt_progress),
                        "met": tgt_progress >= 1,
                    })
                if times > 0 and valid_target_count > 0 and progress >= times:
                    met = True
        remaining = max(0, required_total - progress)
    elif kind == 'never':
        for it in targets:
            t = str(it.get('type') or '').strip()
            n = str(it.get('name') or '').strip()
            if not t or not n:
                continue
            dates = _get_dates_for_target(t, n, for_never=True)
            if _count_in_period_on(dates, period, today) > 0:
                violation = True
                break
        met = not violation

    manual_state = _manual_status_for_date(c, today)
    if manual_state == 'met':
        met = True
        violation = False
    elif manual_state == 'violation':
        violation = True
        met = False

    state = 'violation' if violation else ('met' if met else 'pending')
    return {
        "kind": kind,
        "times": times,
        "period": period,
        "targets": targets,
        "progress": progress,
        "required_total": required_total,
        "remaining": remaining,
        "target_progress": target_progress,
        "met": met,
        "violation": violation,
        "state": state,
        "manual_state": manual_state,
        "triggers": triggers,
    }


def _get_completion_dates(item_type: str, item_name: str) -> list[str]:
    data = read_item_data(item_type, item_name)
    if not data:
        return []
    dates = data.get('completion_dates') or []
    if not isinstance(dates, list):
        return []
    return [d for d in dates if isinstance(d, str)]


def _run_script(script_path: str):
    try:
        # Prefer .chs execution via Console
        from modules import console as ConsoleModule# type: ignore
        if script_path.lower().endswith('.chs'):
            # Use subprocess to call console with script (ensures same behavior as CLI)
            import sys as _sys, os as _os
            root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
            subprocess.Popen([_sys.executable, os.path.join(root, 'modules', 'console.py'), script_path], cwd=root)
        else:
            # Try to run as a console command: e.g., "echo Hello"
            ConsoleModule.run_command('cmd', [script_path], {})
    except Exception:
        pass


def _create_item(item_type: str, name: str, properties: dict):
    try:
        generic_handle_new(item_type, name, properties or {})
    except Exception:
        pass


def evaluate_and_trigger():
    """
    Scans all commitments and fires triggers when their conditions are met.
    Supported patterns:
      - frequency: { times: N, period: day|week|month }, associated_items: [{type,name},...]
      - never: true, forbidden_items: [{type,name},...]
      Triggers: triggers: { on_met: [...], on_violation: [...] }
        action entries can be:
          - { type: 'script', path: 'scripts/my.chs' }
          - { type: 'achievement', name: '...', properties: {...} }
          - { type: 'reward', name: '...', properties: {...} }
    """
    all_commitments = list_all_items('commitment')
    today_dt = _periods().today()
    today_str = today_dt.strftime('%Y-%m-%d')
    for c in all_commitments:
        if not isinstance(c, dict):
            continue
        name = c.get('name') or 'Commitment'
        status = get_commitment_status(c, today=today_dt)
        met = status["met"]
        violation = status["violation"]
        triggers = status["triggers"]
        period = status["period"]
        period_key = _period_key(today_dt, period)

        # Prevent duplicate triggers per day
        state_changed = False
        if met and not violation:
            last = c.get('last_met')
            if last != period_key:
                for action in (triggers.get('on_met') or []):
                    _perform_action(action, name)
                c['last_met'] = period_key
                state_changed = True
        if violation:
            lastv = c.get('last_violation')
            if lastv != period_key:
                for action in (triggers.get('on_violation') or []):
                    _perform_action(action, name)
                c['last_violation'] = period_key
                state_changed = True

        if state_changed:
            try:
                write_item_data('commitment', name, c)
            except Exception:
                pass


def _perform_action(action: dict, commitment_name: str):
    if not isinstance(action, dict):
        return
    at = str(action.get('type') or '').lower()
    if at == 'script':
        p = action.get('path') or action.get('script')
        if isinstance(p, str) and p:
            _run_script(p)
    elif at == 'achievement':
        nm = action.get('name') or f"{commitment_name} achievement {datetime.now().strftime('%Y-%m-%d')}"
        props = action.get('properties') if isinstance(action.get('properties'), dict) else {}
        _create_item('achievement', str(nm), props)
    elif at == 'reward':
        nm = action.get('name') or f"{commitment_name} reward {datetime.now().strftime('%Y-%m-%d')}"
        props = action.get('properties') if isinstance(action.get('properties'), dict) else {}
        _create_item('reward', str(nm), props)


def _print_commitment(name: str):
    data = read_item_data(ITEM_TYPE, name)
    if not data:
        print(f"Commitment '{name}' not found.")
        return
    freq = data.get('frequency') if isinstance(data.get('frequency'), dict) else None
    assoc = data.get('associated_items') if isinstance(data.get('associated_items'), list) else []
    forb = data.get('forbidden_items') if isinstance(data.get('forbidden_items'), list) else []
    print("--- Commitment ---")
    print(f"  Name: {name}")
    print(f"  Description: {data.get('description') or data.get('notes') or 'N/A'}")
    if freq:
        print(f"  Target: {freq.get('times')} per {freq.get('period')}")
    if assoc:
        items = ", ".join(f"{it.get('type','?')}:{it.get('name','')}" for it in assoc if isinstance(it, dict))
        print(f"  Associated: {items}")
    if data.get('never') and forb:
        items = ", ".join(f"{it.get('type','?')}:{it.get('name','')}" for it in forb if isinstance(it, dict))
        print(f"  Forbidden: {items}")
    triggers = data.get('triggers')
    if triggers:
        print(f"  Triggers: {list(triggers.keys())}")
    print(f"  Last met: {data.get('last_met') or 'never'}")
    print(f"  Last violation: {data.get('last_violation') or 'none'}")


def _update_properties(name: str, updates: dict):
    if not updates:
        print("No properties provided to update.")
        return
    data = read_item_data(ITEM_TYPE, name)
    if not data:
        print(f"Commitment '{name}' not found.")
        return
    for key, value in updates.items():
        if key is None:
            continue
        data[str(key).lower()] = value
    write_item_data(ITEM_TYPE, name, data)
    print(f"Commitment '{name}' updated.")

