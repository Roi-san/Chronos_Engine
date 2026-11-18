# Scheduling (Kairos Only)

## Purpose
Operate Chronos scheduling end-to-end using Kairos only: build plans, repair conflicts, adapt to live-day drift, and explain outcomes with evidence.

Last verified: 2026-11-18 against `modules/scheduler/kairos_v2.py` and `commands/today.py` (Kairos v2, the live scheduler).

## Hard Scope
- Use Kairos paths only.
- The legacy scheduler is archived: `today legacy ...` only prints that it is archived.
- Assume user intent is operational scheduling, not generic item CRUD.

## When To Use
- "Plan/reschedule my day."
- "Why did this block move/get cut?"
- "Why is this item missing today?"
- "I missed blocks, rebuild from now."
- "Preview tomorrow/this/next with current status."
- "Fix anchors/conflicts."

## Source of Truth
- Scheduler entrypoint: `commands/today.py`
- Scheduler engine: `modules/scheduler/kairos_v2.py` (class `KairosV2Scheduler`); goal and commitment pressure in `modules/scheduler/direction.py`. `kairos.py` and `weekly_generator.py` are archived and only raise.
- What Kairos v2 reads from items, templates and settings: `docs/reference/item_properties.md`
- Active schedule output: `user/schedules/schedule_YYYY-MM-DD.yml`
- Manual modifications: `user/schedules/manual_modifications_YYYY-MM-DD.yml`
- Completion logs: `user/schedules/completions/YYYY-MM-DD.yml`
- Decision log: `user/logs/kairos_v2_decision_log_latest.md` (one Markdown file per run, `kairos_v2_decision_log_<timestamp>.md`)

## Kairos Mental Model
Kairos v2 runs these phases in order (full list: `docs/dev/architecture.md`, section 3):
1. Gather settings, current status, today's completions, manual injections and adjustments; check sleep (sleep debt, and whether you are inside a sleep block right now).
2. Pick the day template: eligible for the weekday, then `prioritize:` preferences, then closest status match, then name.
3. Place anchors (`reschedule: never`) and hard injections.
4. Work out the day budget: from now to the next bedtime, or 23:59 when the bedtime is after midnight or there is no sleep block (`docs/scheduling/sleep_after_midnight.md`).
5. Build candidates: template children, plus library items that recur today, have a due date or deadline, or are pushed by a goal or commitment.
6. Drop what was completed or skipped today, and scale down to today's status: lighter version, or keep (within grace, urgent, or important enough), or save it for a better day (`docs/scheduling/status_scale_down_design.md`).
7. Lay out fixed-time slots, fill windows (tag and category filters, by score), fill gaps. Urgent work opens a helper window ("Deadline Window", "Due Window", "Commitment Window", "Goal Window") in the earliest gap it fits.
8. On overflow: lighter versions, then trims, then cuts, only on items that allow them.
9. Quick wins, breathing room, timer handoff, decision log.

Agents should reason in that order when diagnosing outcomes. Kairos v2 has no dependency ordering (`depends_on` is not read).

## Core Commands (Kairos)
- `today`
- `today reschedule`
- `today kairos [options]` (shadow run: writes `schedule_<date>_kairos_v2_shadow.yml`, does not replace the day)
- `today kairos week`: disabled in v2; it prints that weekly generation is deferred.
- `tomorrow [days:N]`, `this <weekday>`, `next <weekday|day|ordinal>` (not tested since the move to v2)

## Kairos Runtime Options (Chronos Syntax)
Read by Kairos v2:
- `template:<name|path>`: force the day template.
- `status:key=value,key=value`: status for this run.
- `prioritize:key=value,key=value` and `custom_property:<prop>`: only steer which day template is chosen. They do not change how items are scored.
- `timer_profile:<name>`: passed to the timer handoff.
- `repair-trim:true|false`, `repair-cut:true|false`, `repair-min-duration:N`, `repair-cut-threshold:N`: overflow relief.

Parsed by `today` but ignored by Kairos v2 (2026-11-18): `buffers:`, `breaks:`, `sprints:`, `ignore-trends`, `quickwins:N`, `status-threshold:`, `days:N`. Quick wins still run from `user/settings/quick_wins_settings.yml`, and breathing room comes from `user/settings/buffer_settings.yml`.

## Scheduling Input Levers

### 1) Status Context
- Update status before significant replans:
  - `status energy:low focus:medium ...`
- Status picks the closest-matching day template, and scales items down when today falls short of their `status_requirements` (see the `status_management` skill).

### 2) Template + Windows
- Day template selection: eligible for the weekday (`days`), then `prioritize:` preferences, then closest status match, then most matched status dimensions, then name. With several eligible templates and no status requirements, the alphabetically first wins; `template:<name>` forces one.
- `window: true` nodes are placement containers. Only the `tags` and `category` filter keys are honoured.
- `timeblock` subtypes: only `free` and `buffer` change placement. A `break` timeblock with a time is placed like any fixed block, and the timer runs it as a break.

### 3) Item Properties That Affect Scheduling
- Anchoring: `reschedule: never` (the only anchor rule in v2; `reschedule: false` is not one).
- Timing and duration: `start_time` / `end_time` (`ideal_*` and `start` / `end` are accepted), `duration` (`30`, `45m`, `1h30m`). An item with no duration cannot be placed.
- Recurrence and urgency: `frequency`, `due_date`, `deadline`. A library item with none of these (and no goal or commitment link) is never considered unless it is in the day template.
- `frequency` (since 2026-11-19, `docs/scheduling/recurrence_design.md`): `daily`; weekday names written out (`monday, thursday`) for fixed days; `weekly`, `monthly`, `quarterly`, `yearly` for once per period. A once-per-period item is planned from its turn until it is done, then not again until the next period; a missed turn comes back daily. Give a weekly item `day: <weekday>` or a monthly item `day: <1-31>` when the user names a day; otherwise leave `day` out and Chronos spreads such items over the period (do not invent days to spread them yourself). Other values (`biweekly`, `weekdays`, `mon`) are not understood and never planned. `new` records `created`; keep it.
- Direction: `goal`, a commitment's `rule` and `targets`, `mini_of` / `mini_variant` (the lighter version).
- Status: `status_requirements`, `status_grace`.
- Overflow relief: `trim: allow` with `max_trim_percent`, `cut: allow`. Everything else is protected.
- Not read by Kairos v2: `flexible`, `essential`, `depends_on`, `auto_inject`, `variants`, `environment`.

### 4) Scoring Inputs
- Weights (0-10, 5 neutral, 0 off) in `user/settings/scheduling_priorities.yml`: Category, Happiness, Due Date, Deadline, Priority Property, Goal Alignment, Commitment Pressure.
- `prioritize:` and `custom_property:` steer template choice only (see above).

## Operational Modes

### A) Normal Build
1. `status ...` (if needed)
2. `today`
3. If output is stale/misaligned: `today reschedule`

### B) Midday Recovery
1. Log reality first (`did`, `mark`, `complete`, `cut`, `trim`, `change`, `shift`)
2. Update status if user state changed
3. `today reschedule` (Kairos plans the time left before bedtime)

### C) Future Preview
1. Set status for expected future state (optional)
2. `tomorrow` / `this` / `next`
3. Use preview to adjust templates/anchors before execution day

### D) Diagnostics-First
1. `today kairos ...` (shadow)
2. Inspect `user/logs/kairos_v2_decision_log_latest.md`
3. Apply targeted fixes
4. Re-run active `today reschedule`

## Safe Intervention Ladder
Use smallest-force intervention first:
1. Status correction (`status ...`)
2. Local schedule edits (`change`, `trim`, `shift`, `cut`)
3. Anchoring critical block (`anchor ... scope:today` or `scope:item`)
4. Reschedule (`today reschedule`)
5. Template/window/property corrections

Avoid jumping straight to template rewrites when a local edit solves the issue.

## Conflict Playbooks

### Overlapping Anchors
Symptoms:
- Two fixed blocks overlap in the plan, or a hard injection (`today inject "<name>" at HH:MM`) is rejected with `anchor_overlap`.
Actions:
1. Kairos v2 does not check authored anchors against each other, so find the overlapping `reschedule: never` nodes in the day template.
2. Move or shorten one of them in the template (or force the injection if that is what the pilot wants).
3. Re-run `today reschedule`.

### Underfilled Day
Symptoms:
- Large gaps, few planned items, many unscheduled candidates.
Actions:
1. Check window filters (only `tags` and `category` count).
2. Check durations: an item with no usable duration is never placed.
3. Check that tasks are in scope: a task that is not in the day template needs a due date, a deadline, or a goal or commitment link.
4. Check `schedule.status_scale_down` in the schedule file: items may have been saved for a better day.
5. Re-run.

### Excessive Cuts/Trims
Symptoms:
- Important work repeatedly cut or trimmed.
Actions:
1. Only items with `cut: allow` or `trim: allow` (and `max_trim_percent`) are cut or trimmed; remove those flags from critical items. Anything else that does not fit is reported as overflow, not cut.
2. Reduce day load (durations, fewer blocks).
3. Increase usable slack (free or buffer blocks).
4. Re-run and inspect the relief notes in the decision log.

### Ordering Problems
Kairos v2 has no dependency ordering (`depends_on` is not read). To keep an order, put the steps inside a routine in that order, or give them fixed times.

## Manual Overrides and Day Control
- Time and duration controls:
  - `change <item> HH:MM`
  - `shift <item> +/-minutes`
  - `trim <item> minutes`
  - `stretch <item> minutes`
- Structural controls:
  - `split <item> [count:N]`
  - `merge <item> with <other>`
  - `cut <item>`
  - `anchor <item> [scope:today|item]`
- Logging reality:
  - `did "Block" start_time:... end_time:... status:...`
  - `mark <item>:completed|skipped|partial|...`
- Putting something back: `today inject "<name>" type:<type>` (Home's Add back button). Items added by hand are never removed by status.

Rule:
- Log reality first, then reschedule.

## Buffers, Breaks, and Timer Alignment
- Kairos v2 does not insert synthetic buffer or break blocks (`buffers:` and `breaks:` are ignored). It leaves breathing room between items and around fixed blocks from `buffer_settings.yml` (`global_dynamic_buffer`), only where the day has spare time (`docs/scheduling/gaps_and_breathing_room.md`).
- Authored `subtype: buffer` blocks absorb overflow. Authored `subtype: break` blocks keep their time.
- In timer schedule mode, break/buffer blocks are treated as break phases (non-completable).
- Do not treat buffer/break blocks as normal completion targets.

## Explainability Contract For Agents
When reporting scheduling actions, always include:
1. What was changed (commands/options used).
2. Why (status/constraint/conflict rationale).
3. What moved/cut/anchored.
4. What user should do next (if any).

Good summary format:
- "Updated status to `energy:low, focus:medium` and ran `today reschedule`."
- "Kairos swapped Gym for Home mobility (energy is low today), kept the meeting, and saved Long run for a better day."
- "Next recommended action: start `Deep Work Lite` block now."

## High-Value Recipes

### Recipe: Overwhelmed Midday
1. `status energy:low focus:low`
2. `did "Morning Block" status:partial`
3. `today reschedule`

### Recipe: Protect Hard Commitments
1. `anchor "Doctor Appointment" scope:today`
2. `anchor "School Pickup" scope:item type:task` (only for items that are in the day template)
3. `today reschedule`

### Recipe: Deadline Bias
1. Raise the `Deadline` and `Due Date` rows in `user/settings/scheduling_priorities.yml` (0-10, 5 is neutral).
2. `today kairos` and check the plan in the decision log.
3. `today reschedule` if approved.

### Recipe: Energy-Adapted Tomorrow Preview
1. `status energy:medium focus:high`
2. `tomorrow`
3. If needed: tune template/status requirements and preview again.

## Guardrails
- Never use legacy scheduler paths; they are archived.
- Avoid destructive structural edits before validating with preview/shadow run.
- Keep anchoring selective; over-anchoring increases conflict risk.
- Do not claim scheduler reasoning without checking decision logs in ambiguous cases.
- Use explicit dates when editing non-today schedules.

## References
- `docs/dev/architecture.md` (Kairos v2 phases)
- `docs/reference/item_properties.md` (what Kairos v2 reads)
- `docs/scheduling/status_scale_down_design.md`, `docs/scheduling/sleep_after_midnight.md`, `docs/scheduling/gaps_and_breathing_room.md`, `docs/scheduling/direction_goals_commitments.md`
- `docs/reference/cli_commands.md`
- `docs/agents/agents.md`
- `docs/scheduling/scheduling_algorithm_overview.md` and `scheduling_algorithm_deep_dive.md` describe the archived v1 scheduler.
