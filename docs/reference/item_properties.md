# Standard Item Properties

Last verified: 2026-11-17 (timeblock breaks and the timer, and assumed lengths: 2026-11-18) against `modules/scheduler/kairos_v2.py`, `modules/scheduler/runtime.py`, `modules/scheduler/direction.py`, `modules/scheduler/v1.py` (template helpers), `modules/scheduler/sleep_gate.py` and `modules/item_manager.py`.

This is a practical reference of item properties that Chronos actively uses today, with the emphasis on what the active scheduler (**Kairos v2**) does with each one. Where a property is written by a builder or wizard but ignored by Kairos v2, it is listed under [Not read by Kairos v2](#not-read-by-kairos-v2).

Keys are case-insensitive at the top level of an item file: `Name:` and `name:` are the same (`ItemManager.read_item_data` and Kairos both lowercase top-level keys). Nested keys, such as those inside `status_requirements` or `filters`, are matched as written but compared case-insensitively.

## General (all item types)

- `name` (string): Human-readable name. The scheduler identifies an item by `type` + `name`, and completion logs match by name.
- `type` (string): Item type (task, habit, routine, ...). Determines the storage folder and behavior.
- `status` (string): Common values `pending`, `completed`, `skipped`, `partial`. Kairos skips items whose `status` is `inactive`, `archived`, `disabled` or `paused`. It does **not** skip `status: completed`; see the note under `due_date`.
- `tags` (list): Used by window filters, dashboards and `list`/`find`/`for` filters. Always stored as a list; a comma string given on the console is split.
- `category` (string): Ranked in `user/settings/category_settings.yml`; used in scoring and in window filters.
- `priority` (string): Ranked in `user/settings/priority_settings.yml`; used in scoring.
- `duration` (number or string): Length in minutes. Accepted: `30`, `"30"`, `1h`, `1.5h`, `15m`, `90 min`, `1h30m`, `2h 15m`. Since 2026-11-18 an item without a usable length is still planned (see [Lengths Kairos assumes](#lengths-kairos-assumes)); before, it could never be placed.
- `sleep` (bool): Canonical sleep marker. Kairos also treats an anchor as sleep when its category is `sleep`, it is tagged `sleep`, or its name contains "sleep" or "bedtime". Prefer `sleep: true`. A sleep anchor in the day template sets where the plan ends; see [Bedtime: where the plan ends](#bedtime-where-the-plan-ends).

### Lengths Kairos assumes

Decided 2026-11-18 (D1). Full rule, tests and verification: `docs/scheduling/item_lengths.md`.

- An item's own length always wins; a block with a start and an end time is as long as that span.
- A **task or habit** with no length (or `duration: 0`, which `new` writes) is planned for `default_duration_minutes` from `user/settings/scheduling_settings.yml`, 30 minutes when not set.
- A **routine, subroutine or microroutine** with no length of its own is planned as one block for the total of its steps' lengths (steps without a length count 0; nested routines add up). If none of its steps has a length, the routine gets the default once. Its steps are covered by that block, so they are not planned a second time.
- Anchors, sleep blocks, windows and timeblocks are left alone.
- Every assumed length is listed in `schedule.assumed_lengths` (`source`: `default` or `steps`). Home tags blocks planned with the default **no length** and says why in their tooltip.

## How an item gets into a day (Kairos v2)

Kairos considers two sources of work:

1. **The chosen day template.** Every direct child of the day template is a candidate, except anchors (placed separately), windows, and `free`/`buffer` blocks.
2. **The item library** (`user/habits`, `user/tasks`, `user/routines`, `user/subroutines`, `user/microroutines`, `user/timeblocks`). An item from these folders is a candidate only if at least one of these is true:
   - `frequency` applies to the day;
   - it has a `due_date`;
   - it has a `deadline`;
   - a goal it serves is active, or a commitment that counts it is unmet (see [Goals and commitments](#goals-and-commitments)).

   An item with none of these never reaches the plan, even if a window's tag filter would match it.

Library items are always skipped when they are bad habits (`polarity: bad`), anchors (`reschedule: never`), sleep blocks, windows, or `free`/`buffer` blocks.

### Recurrence

- `frequency` (string or list): `daily`, a weekday name (`monday` ... `sunday`), or several, as a list or a comma/slash string (`monday, wednesday`). `weekly` currently matches **every** day: Kairos does not track which day of the week a weekly item belongs to, so give weekday names instead. `monthly`, `quarterly` and `yearly` match **no** day, so such items are never planned (issue 10; the proposed fix is `docs/scheduling/recurrence_design.md`).

### Due dates

- `due_date` (YYYY-MM-DD): Brings the item into scope and adds urgency: overdue or today +20, tomorrow +10, within 3 days +5 (at the shipped weights in `scheduling_priorities.yml`).
- `deadline` (YYYY-MM-DD): Same, stronger: +25 / +12 / +6.

### Finished one-off items

An item with no `frequency` whose `status` is `completed`, `complete`, `done`, `cancelled`, `canceled`, `abandoned` or `dropped` is not brought back by its due date, deadline or goal. `mark "<name>":completed` and `complete task <name>` both write `status: completed` onto such items. To reopen one, set its `status` back to `pending`.

An unmet commitment can still bring a finished one-off back, because commitment targets are meant to repeat. Recurring items (with a `frequency`) are never hidden by their `status`. The decision log lists what was left out under `finished_one_offs_skipped`.

### Skipped today

An item marked skipped today is not handed back by `today reschedule` for the rest of the day.

## Day templates

- `days` (list or string): Weekday names the template is eligible for (`[monday, tuesday]`). A template with no `days` is eligible every day.
- `status_requirements` (map): See [Status](#status). On a day template it makes the template a closer or worse match for today.
- `children` (list): The template's structure. `sequence` at the root of a template is also read for ordering. Kairos v2 does not expand `items`.

How the template is chosen:

1. Templates eligible for the weekday are collected from `user/days/`.
2. They are ranked by: the `prioritize:` preferences passed to `today`, then closest status match, then most matched status dimensions, then **name**.
3. The first wins, so with several eligible templates and no status requirements, the alphabetically first one is used. `template:<name>` on the command line forces one.

### Inheritance

A template child takes these properties from its parent template unless it sets its own: `category`, `theme`, `status_requirements`, `priority`, `priority_property`, `happiness`, `planet`, `days`, `tags`, `window`, `filters`. The item file the child points at can override the parent, and the child node in the template can override both.

## Fixed times, anchors, windows

### Times

- `start_time` / `end_time` (HH:MM): The fields Kairos places by.
- `ideal_start_time` / `ideal_end_time`, `start` / `end`: Accepted as fallbacks when `start_time` / `end_time` are missing; the Day Builder and Routine Builder write `ideal_*`. An explicit `start_time` / `end_time` always wins.

A template node with a start and an end (or a start and a duration) that is not an anchor, window, free or buffer block is placed as a **fixed-time block** at that time. On a day that falls short of its `status_requirements` (on the node or on the item it points at), the same scale-down rule as for flexible items applies, keeping the start time: the lighter version takes the slot for its own length, or the slot is kept (within grace, urgent, important) or freed so other work can use the time. See [Status](#status).

### Anchors

- `reschedule: never`: The only rule that makes something a hard anchor in Kairos v2. `reschedule: false` does not. Anchors are placed first and are never moved, trimmed or cut. Kairos v2 does not check authored anchors against each other, so keep them from overlapping; a hard injection that overlaps an anchor is rejected unless it is forced.

Anchors come only from the chosen day template (at any depth under `children`) and from hard injections. A library item marked `reschedule: never` that is not in the day template is not scheduled at all. `anchor "<name>" scope:item` writes exactly this onto the item file, so only use it on items that are in your day template.

### Bedtime: where the plan ends

Verified 2026-11-18 (`model_day_budget`, `_resolve_next_bedtime`). Full rule, decisions and tests: `docs/scheduling/sleep_after_midnight.md`.

Sleep anchors (a `reschedule: never` node that counts as sleep, see `sleep` above) are not placed as blocks. Their `start_time` is the bedtime, and flexible work is planned only up to the next bedtime:

- A sleep anchor starting at **12:00 or later** is a bedtime today (`23:30` ends the plan at 23:30).
- A sleep anchor starting **between 00:00 and 11:59** is a bedtime **after midnight**. It ends the day *before* it, so the plan runs to **23:59** and nothing is placed past the end of the calendar day. Only after midnight, while it is still ahead (00:30 with a `02:00` bedtime), does the plan run up to it.
- With several sleep anchors, the soonest upcoming bedtime wins. Other sleep anchors (naps) are not kept free of work, and a nap at 14:00 ends the day at 14:00 (known issue 8 in `docs/ISSUES_AND_NEXT_STEPS.md`).
- **No sleep anchor**: the plan runs to 23:59 (before 2026-11-18 it stopped at 16:00, 24 hours minus the target sleep).
- After "go back to sleep" or "Shift today later" in the sleep prompt, the plan starts when the sleep block ends.

`schedule.day_budget` records where the plan stops (`sleep_boundary_time`, `sleep_boundary_source`: `sleep_anchor`, `sleep_anchor_after_midnight` or `no_sleep_anchor`) and the real bedtime (`bedtime_time`, `bedtime_day`: `today` / `tomorrow`, `bedtime_anchor`).

### Windows

A window is a template node that Kairos fills with the best-ranked matching candidates.

- `window: true`
- `start` / `end` (HH:MM), or `start_time` / `end_time`, or `ideal_start_time` / `ideal_end_time`.
- `filters` (map): Only two keys are honored:
  - `tags`: a candidate must share at least one tag.
  - `category`: a candidate's category must match exactly.

  Other filter keys (type, priority, custom properties) are not applied.
- `category` on the window itself (without a filter) is a soft preference: matching items score higher but others can still fill it.

### Gaps and breathing room

Verified 2026-11-18. Full rule and decisions: `docs/scheduling/gaps_and_breathing_room.md`.

- Flexible work fills the free gaps between fixed blocks, highest score first, earliest gap first. Urgent work (due today, deadline, a strong goal or commitment push, added by hand) opens a helper window in the **earliest gap it fits in**. `scheduling_settings.yml` `runtime_helper_windows.minimum_gap_minutes` can demand a bigger gap; the default is any gap that fits (it was 30 minutes).
- **Breathing room**: `buffer_settings.yml` `global_dynamic_buffer` (`buffer_duration_minutes`, `buffer_interval_minutes`, shipped 5 and 5). Kairos leaves that margin after a fixed block, between items once the interval of work has run, and before the next fixed block, but only where the stretch has spare time. It never changes which items are planned. The margin before a fixed block wins when there is room for only one. With no `global_dynamic_buffer` section it is off. `template_buffers` are not applied.

### Timeblocks

- `type: timeblock`
- `subtype`: Only `free` and `buffer` have scheduler meaning (the same words as tags work too). A `free` block is intentionally open time; a `buffer` block absorbs overflow. Other subtypes (`category`, `break`) are treated as ordinary blocks. A `break` with a fixed time keeps its time, and the timer (`start day`) runs it as a break, like a buffer: no completion prompt, no points (since 2026-11-18; before, it was run as work).
- `duration`: Total block time.

## Status

- `status_requirements` (map): Status dimension to an allowed value or list of values, for example `{energy: [high, medium], health: good}`. Dimensions and their value order come from `user/settings/status_settings.yml` and `user/settings/<dimension>_settings.yml`.

- `status_grace` (number, optional): Steps this item may fall short on any dimension before it can be left out. Overrides the dimension's `Grace`. `0` = strict, larger = more forgiving.

Each dimension's values are ordered by the `value` number in its settings file, 1 = best (Energy: High 1, Medium 2, Low 3, Exhausted 4). The importance of each dimension is its `Rank` in `status_settings.yml` (1 = most important); a row may also set `Grace: <steps>` (default 1). `place` is skipped, and unknown dimensions or values are ignored. Keys and values are case-insensitive.

### On an item: one-way fit and scale-down

For an item, only being **worse** than it needs counts; being better than needed is never a mismatch. For each dimension it names, Kairos counts how many steps today is below the worst value it accepts. Then:

1. **Nothing short**: scheduled.
2. **Short, and a lighter version exists** (`mini_of` / `mini_variant`, not more demanding than the full one): the lighter version is scheduled instead, even if it is short too. It keeps the goal and commitment pressure.
3. **Short, no lighter version, within grace** on every dimension (default: one step): scheduled.
4. **Further short**:
   - **urgent** (due date or deadline today or overdue, or a commitment at "last chance" / "behind"): scheduled;
   - else **importance vs strain**: scheduled if importance >= strain - 0.1, otherwise **saved for a better day** (left out today, recorded with the reasons).

Strain = sum over dimensions of (steps short - grace) x dimension weight, where the top-ranked dimension weighs 1.0 and the rest fall by rank (shipped: Health 1.0, Energy 0.71, Focus 0.43). Importance = the strongest of the item's commitment pressure, goal pressure and own `priority` (critical 1.0, high 0.7, medium 0.4), each times its weight in `scheduling_priorities.yml` / 5 (Commitment Pressure, Goal Alignment, Priority Property).

Fixed slots in the day template follow the same rule at their own time (see [Fixed times](#fixed-times-anchors-windows)). Items added by hand (`today inject "<name>"`, which is what Home's **Add back** button runs) and anchors are never removed by status; a fixed slot added back keeps its own time. Home lists what was saved under "Saved for a better day". What happened is in `schedule.status_scale_down` (`swapped`, `kept` with the reason, `saved` with strain and importance). Full design, worked examples and decisions: `docs/scheduling/status_scale_down_design.md`.

The same one-way distance also sets what is cut first when the day overflows (a poor fit is easier to sacrifice) and ranks `inject:next`.

### On a day template

Template choice keeps the **two-way closest match** (see "How the template is chosen"), so a "Sick Day" template does not also win on a healthy day.

Legacy top-level status keys (for example `energy: high` directly on an item) are not read by Kairos v2; use `status_requirements`.

## Trimming and cutting

When the day overflows, Kairos only shortens or removes items that allow it. Everything else is protected by default.

- `trim: allow` together with `max_trim_percent: <0-100>`: The item may be shortened by up to that share, never below a minimum length. `trim: allow` with no `max_trim_percent` is treated as not trimmable.
- `cut: allow`: The item may be removed entirely.

Order of relief:

1. Items that did not fit are swapped for a shorter authored lighter version (`mini_of`), if one exists.
2. Trims, least important first.
3. Cuts, least important first.
4. Whatever still does not fit is reported, not forced in.

"Least important" is the lowest keep-score: category, priority, happiness, urgency, goal and commitment pressure, and status fit (a poor fit lowers it). Trimming and cutting can be switched off per run (`repair_trim`, `repair_cut` in the Today widget).

## Goals and commitments

Full detail and the numbers: `docs/scheduling/direction_goals_commitments.md`.

- `goal` (string, on a task or habit): The goal this item serves. Also read: a goal's `supporting_habits`, a milestone's `criteria` / `links`, and a task's `project` when that project has a `goal`.
- On a goal: `target_date`, `priority`, `status` (completed, archived, cancelled and on-hold goals push nothing).
- On a commitment: `rule: {kind: frequency, times: N, period: day|week|month}` and `targets: [{type: habit, name: ...}]`. "Never" commitments are not scheduled.
- `mini_of` (string, on the lighter item) or `mini_variant` (string, on the full item): Links a full item to a lighter version. The lighter one is used on days the full one's `status_requirements` do not fit, and when the full one does not fit in the day (if the lighter one is shorter). It inherits the goal and commitment pressure and counts toward the commitment.

## Scoring inputs

- `happiness` (string or list): Keys from `user/settings/map_of_happiness.yml`; the best-ranked one adds to the score.
- `category`, `priority`, `due_date`, `deadline`, goal and commitment pressure: see above.
- The weight of each factor is set in `user/settings/scheduling_priorities.yml`. (`today ... prioritize:key=value` only steers which day template is chosen; it does not change these weights.)

## Not read by Kairos v2

These are still written by some builders and wizards, and were used by the archived v1 scheduler, whose code in `commands/today.py` is unreachable. Kairos v2 ignores them.

| Property | Written by | Notes |
| --- | --- | --- |
| `essential` | Life Setup wizard, Sleep Settings widget, `template` command | Only read by the sleep-conflict check (`sleep_gate.py`), where it marks a sleep block as fixed. Not used to protect items from cuts; use the defaults above (everything is protected unless `cut: allow`). |
| `flexible` | Template Builder, Life Setup, Sleep Settings | No effect. |
| `absorbable` | Life Setup, Sleep Settings | Recorded on free/buffer blocks; no effect on placement. |
| `depends_on` | Template Builder | Kairos v2 has no dependency ordering. |
| `variants` | | Use `mini_of` / `mini_variant` instead. |
| `auto_inject` | | Use a manual injection, or `inject:next`. |
| `reschedule_policy` | | No effect. |
| `environment` | | Deferred in v2. |

## Notes

- Defaults can be set per item type in `user/settings/<type>_defaults.yml`.
- Project and goal planning fields like `state`, `stage`, `priority` and `target_date` are supported in dashboard planning views. `stage` is free text.
