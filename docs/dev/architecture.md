# Chronos Architecture

This guide explains how Chronos fits together so you can extend it confidently.

## Runtime Overview

### 1. CLI Entrypoint (`modules/console.py`)
  - Adds project paths, sets UTF-8, and loads `commands/*.py` dynamically.
  - Parses interactive input, CLI args, and `.chs` scripts (supports nested `if/elseif/else/end` and loop blocks).
  - Uses `modules/variables.py` for in-memory variables and token expansion (e.g., `@nickname`, `@status_energy`).
  - Macro hooks: command execution is wrapped with BEFORE/AFTER hooks via `modules/macro_engine.py` (enabled by `user/scripts/macros/macros.yml`). Dashboard calls also pass through these hooks.
  - Autosuggest and autocomplete are registry-driven; see `docs/dev/autosuggest.md` for the slot model and refresh workflow.

### 2. Item System (`modules/item_manager.py`)
Items are the atoms of Chronos. They are stored as YAML files in the `user/` directory.
- **Polymorphic**: Any item can have `tasks`, `subroutines`, `inventory_items`, or `milestones`.
- **Fractal**: Items can nest indefinitely. The `Scheduler` creates a flattened view for execution but preserves the hierarchy for planning.
- **Defaults**: Each item type has a `_defaults.yml` (e.g., `task_defaults.yml`) that defines its initial state.

### 3. The Scheduler (Kairos v2)
- **Command Router**: `commands/today.py`.
  - `today`, `today reschedule`: run Kairos v2 and save the day (the active path).
  - `today kairos ...`: a shadow run with explicit options; writes `user/schedules/schedule_<date>_kairos_v2_shadow.yml` and does not replace the day.
  - `today kairos week`: disabled; it prints that weekly generation is deferred until a v2-native replacement exists.
  - `today legacy ...`: prints that the legacy scheduler is archived and stops. The old inline scheduler code further down `today.py` ("Mode C") is unreachable.
- **Kairos Engine**: `modules/scheduler/kairos_v2.py`, class `KairosV2Scheduler`. `generate_schedule()` runs these phases in order:
  1. `gather_information`, `model_reality`: settings, current status, completion logs for the day, manual injections and adjustments.
  2. `model_sleep`, `commit_sleep`: sleep debt, and whether you are inside a sleep block right now (and what the sleep prompt answered).
  3. `ensure_week_context`, `select_week_template`, `derive_week_days`, `select_day_template`: pick the day template (eligible for the weekday, then `prioritize:` preferences, then closest status match, then name).
  4. `commit_anchor_skeleton`: place `reschedule: never` anchors from the template and hard injections.
  5. `model_day_budget`: where the plan ends (the next bedtime from the template's sleep anchors; 23:59 when that bedtime is after midnight or there is none; `docs/scheduling/sleep_after_midnight.md`) and how much flexible time is left before it.
  6. `build_candidate_universe`: template children plus library items that recur today (`recurrence.py`: daily, weekday names, or a weekly to yearly item from its turn until done), have a due date or deadline, or are pushed by a goal or commitment (`direction.py`). An item without a length gets one here: the default (`default_duration_minutes`), or for a routine the total of its steps (`docs/scheduling/item_lengths.md`).
  7. `remove_reality_impossible_candidates`: drop what was completed or skipped today; scale down to today's status (`_scale_down_for_status`: swap in lighter versions, keep within grace / urgent / important items, save the rest for a better day; see `docs/scheduling/status_scale_down_design.md`).
  8. `shape_week`, `populate_day_and_windows`, `narrow_window_candidate_pools`, `select_window_contents`: lay out fixed-time structure and fill windows by tag/category filter and score.
  9. `handle_gaps_buffers_and_recovery`, `build_runtime_helper_windows`, `place_remaining_structure`: fill gaps, open helper windows for urgent work the template has no place for ("Deadline Window", "Due Window", "Commitment Window", "Goal Window", "Manual Opportunity Window", "Best Next Window" for `inject:next`), place remaining items.
  10. `run_pressure_relief_pipeline`: on overflow, lighter versions, then trims, then cuts, only on items that allow them.
  11. `fill_quick_wins`, `finalize_conceptual_schedule`, `build_timer_handoff`, `persist_decision_log_artifact`. Building the conceptual blocks ends with breathing room (`_apply_breathing_room`): margins from `buffer_settings.yml` around placed work, using only spare time (`docs/scheduling/gaps_and_breathing_room.md`).
- **Inputs**: Kairos v2 reads the YAML files under `user/` directly (`days`, `weeks`, `habits`, `tasks`, `routines`, `subroutines`, `microroutines`, `timeblocks`, goals, milestones, commitments, `settings`). It does not read the SQLite mirrors, and trend input is a placeholder that does not affect planning yet. Which item properties it honors: `docs/reference/item_properties.md`.
- **Supporting modules** in `modules/scheduler/`:
  - `direction.py`: goal, commitment and recurring pressure (`docs/scheduling/direction_goals_commitments.md`).
  - `periods.py`: the one shared helper for days and periods (what day it is, period bounds and keys, the completion logs, "was it done"); used by commitments, recurring items and Home (`docs/scheduling/recurrence_design.md`).
  - `recurrence.py`: recurring items, their turns (a picked `day:` or spread over the period) and whether they are on today's plan (`docs/scheduling/recurrence_design.md`).
  - `runtime.py`: the saved day format and the timer's execution plan.
  - `sleep_gate.py`: the sleep-conflict check that runs before commands which would schedule into sleep.
  - `v1.py`: template and schedule-file helpers. Kairos v2 uses its template readers; `trim`, `cut`, `shift`, `stretch`, `split`, `merge`, `anchor`, `change` and `mark` use its schedule-file editors.
  - `kairos.py`, `weekly_generator.py`: archived. Both only raise an error pointing at the archive.
- **Output**: `user/schedules/schedule_YYYY-MM-DD.yml` (the day runtime payload) and decision logs in `user/logs/kairos_v2_decision_log_*.md` (`kairos_v2_decision_log_latest.md` is the most recent).
- **Compatibility Layer**: Kairos output is adapted into the legacy schedule row shape in `commands/today.py` so the dashboard, API and schedule-edit commands keep working.
- **Manual Modifications**: Persisted in `user/schedules/manual_modifications_YYYY-MM-DD.yml`; `today.py` turns them into Kairos injections and adjustments on the next run.

### 4. Conditions Engine (`modules/conditions.py`)
A recursive descent parser that evaluates logic strings in scripts and triggers.
- **Grammar**: Supports `( ... )`, `AND`, `OR`, `XOR`, `NOT`.
- **Operators**: `==`, `!=`, `>`, `<`, `matches` (Regex).
- **Targets**: Can check file existence (`exists file:...`), environment variables (`exists env:...`), or item properties (`task:MyTask:status == completed`).

### 5. Sequence System (`modules/sequence`)
The "Long-Term Memory" of Chronos.
- **Mirroring**: Mirrors the YAML data into SQLite databases (`chronos_core.db`, `chronos_matrix.db`, `chronos_events.db`, `chronos_behavior.db`, `chronos_journal.db`) for fast querying by the dashboard, reviews and agents. Kairos v2 does not read them.
- **Trends**: Analyzes history to build `chronos_trends.db` and generates a `trends.md` digest.
- **Automation**: Runs automatically via `automation.py` hook during the nightly rollover.
- **Cleanup Integration**: The `clear` command provides surgical control over Sequence Mirrors:
  - `clear cache` - Deletes all `.db` files, forcing full rebuild
  - `clear db:<name>` - Deletes specific mirror (e.g., `chronos_matrix.db`), auto-rebuilds on next access
  - `clear registry:<name>` - Clears in-memory registry caches (wizards, themes, etc.) to force YAML reload
  - See [Admin Tools](../features/admin_tools.md) for full cleanup reference

### 6. Listener (`modules/listener/listener.py`)
  - Monitors time for alarms/reminders, triggers sounds (pygame.mixer), handles timer ticks.
  - Can execute scripts and target actions (e.g., complete task on trigger).

### 7. Dashboard (`utilities/dashboard`)
  - Server (`server.py`) serves assets and JSON/YAML APIs (ThreadingHTTPServer over plain HTTP).
  - UI is plain ES modules + a small loader (`core/runtime.js`) to mount views (`Home` is the default landing page; also `Calendar`, `TemplateBuilder`, `Cockpit` and others under `utilities/dashboard/views/`), widgets (Scheduler/Today widget, Item Manager, Variables, Terminal, Habit Tracker, Goal Tracker, Commitments, Rewards, Achievements, Milestones, Notes, Journal, Profile, Review, Timer, Settings, Clock, Status, Debug), and dock gadgets (`utilities/dashboard/gadgets/*`).
  - Widgets mount via attributes, e.g., `data-widget="Notes"`, and export `mount(el, context)`. Cockpit panels register via `window.__cockpitPanelRegister` and render inside the drag-and-drop canvas.

## Dashboard Architecture

The Dashboard is a hybrid Desktop/Web application.

### Backend (`utilities/dashboard/server.py`)
A `ThreadingHTTPServer` that acts as the bridge between the browser and the file system.
- **API**: Provides JSON endpoints (`/api/profile`, `/api/cockpit/matrix`, `/api/media/mp3`) to read/write system state.
- **Streaming**: Streams MP3s from `user/media` for the music player.
- **Bundler**: The `dashboard` CLI command pre-bundles static settings into `generated/settings_bundle.js` for fast startup.

### Frontend (`utilities/dashboard/app.js`)
A generic Vanilla JS Single Page Application (SPA).
- **Module Loader**: Dynamically imports "Panels" (views) and "Wizards" to keep the initial bundle small.
- **View System**: Manages a tiling window interface (`view-panes`) where users can open multiple tools side-by-side.
- **Widgets**: Persistence-aware widgets (Notes, Timer, Status) that float over the UI.
- **Theming**: Supports hot-swappable CSS themes (Blue, Amber, Emerald, Rose).
  - Endpoints (selected):
    - Health: `GET /health`.
    - Today API: `GET /api/today`, `POST /api/today/reschedule`.
    - CLI bridge: `POST /api/cli` — invokes the console pipeline in-process (falls back to subprocess if needed).
    - Profile & Theme: `GET /api/profile`, `GET /api/theme?name=...`.
    - Variables: `GET/POST /api/vars`, `POST /api/vars/expand`.
    - Items: `GET /api/items`, `GET /api/item`, `POST /api/item`, `POST /api/item/copy|rename|delete`, bulk `POST /api/items/delete|setprop|copy|export`, `POST /api/open-in-editor`.
    - Template Builder: `GET /api/template/list`, `GET /api/template`, `POST /api/template`.
    - Habits & Goals: `GET /api/habits`, `GET /api/goals`, `GET /api/goal?name=...`.
    - Commitments & Milestones: `GET /api/commitments`, `GET /api/milestones`, `POST /api/milestone/update`.
    - Rewards & Points: `GET /api/points`, `GET /api/rewards`, `POST /api/reward/redeem`.
    - Achievements: `GET /api/achievements`, `POST /api/achievement/update`.
    - Timer: `GET /api/timer/status|profiles|settings`, `POST /api/timer/start|pause|resume|stop|cancel|confirm`.
    - Settings: `GET /api/settings`, `GET /api/settings?file=Name.yml`, `POST /api/settings?file=Name.yml` (raw YAML preserved).
  - Security: permissive CORS for local dev; do not expose publicly without adding auth and controls.

- UI runtime (`utilities/dashboard/app.js` + widgets/views)
  - Views: Calendar, Template Builder, and the Cockpit canvas (panels under `utilities/dashboard/panels/`).
  - Widgets: Scheduler (Today widget), Item Manager, Variables, Terminal, Habit Tracker, Goal Tracker, Commitments, Rewards, Achievements, Milestones, Notes, Journal, Profile, Review, Timer, Settings, Clock, Status, Debug Console.
  - Gadgets + Dock: Bottom dock (`#chronosDock`) populated by gadget registry (`GET /api/registry?name=gadgets`); gadgets mount via `mountGadget()` and can be toggled from the topbar Gadgets menu.
  - Event bus: `mount(el, context)` receives a `context.bus` used by widgets (e.g., emit `vars:changed`, `widget:show`, `calendar:selected`).
  - Terminal: runs CLI via `/api/cli`, supports history, Ctrl+L, optional variable expansion.
  - Item Manager: search/sort/multi-select, YAML editor, copy/rename/delete; bulk delete/set property/copy/export (exports to `/temp/exports_items_*.zip`).

## Data Model

- Items are YAML files with a `name`, `type`, and optional fields.
- Hierarchy allows nested children (routines → subroutines → microroutines → items).
- Schedules store computed blocks for the current day; completions are tracked.

## Settings

- Location: `user/settings/`
- Conventions:
  - Prefer lowercase filenames, e.g., `points_settings.yml`, `achievement_defaults.yml`, `<item>_defaults.yml`.
- Timer files use lowercase canonical names (for example `timer_settings.yml` and `timer_profiles.yml`).
- The Settings widget and `/api/settings` simplify editing.

## Dashboard API (summary)

- CLI: `POST /api/cli` — runs commands in-process; subprocess fallback.
- Variables: `GET/POST /api/vars`, `POST /api/vars/expand`.
- Profile/Theme: `GET /api/profile`, `GET /api/theme?name=...`.
- Items: `GET /api/items`, `GET /api/item`, `POST /api/item*`, bulk ops including `export`.
- Today API: `GET /api/today`, `POST /api/today/reschedule`.
- Timer: `GET /api/timer/status|profiles|settings`, `POST /api/timer/start|pause|resume|stop|cancel|confirm`.
- Settings: `GET/POST /api/settings` and `GET /api/settings?file=...`.

## Extending Chronos

- Add a command
  1. Create `commands/my_command.py` with `run(args, properties)`.
  2. Add `get_help_message()` to integrate with `help`.

- Add an item module
  1. Create `modules/my_item/main.py` with `handle_<verb>` or `handle_command`.
  2. Reuse `ItemManager` for common behaviors (`new`, `append`, `delete`).

- Add a widget, view, panel, popup, or gadget
  1. Create folder in `utilities/dashboard/widgets/<Name>/` (or Views/Panels/Popups/Gadgets)
  2. Create `index.js` with appropriate export function (`mount()` for widgets/views/popups/gadgets, `register()` for panels)
  3. (Optional) Add metadata YAML file for custom labels or post-release badges
  4. Refresh dashboard - component auto-discovered and added to menu
  5. Add server endpoints if needed; prefer JSON responses for easy parsing

- Add a Wizard or Theme
  - Wizards: Create folder in `utilities/dashboard/wizards/<Name>/` with `index.js`
  - Themes: Drop CSS file into `utilities/dashboard/themes/`
  - Component auto-discovered on server restart
  - See `docs/dev/extensibility.md` for the full specification

## Best Practices

- Keep modules small and composable.
- Prefer JSON over YAML for HTTP responses (clients parse easier); YAML is OK for human-readable responses.
- Validate inputs on the server; sanitize paths; avoid blocking I/O in handlers.
- For long-running or external operations, apply timeouts and consider subprocess isolation.










