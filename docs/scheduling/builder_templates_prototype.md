# Prototype: scheduling days authored in the dashboard builders

Status: prototype on branch `home-hub`, based on `alpha_v0.3` (`07a2bf1`). Not merged. Written for review.

## The problem

A day built with the Day Builder, Routine Builder or Life Setup wizard did not schedule. With a realistic data set (sleep anchor, two tag-filtered windows, meals, a morning and an evening routine, five tasks, five habits) `today reschedule` at 15:25 produced one block: the morning routine, placed in a gap. Windows, anchors and the evening routine were missing and the day ended at 16:00.

Five independent causes, each small:

| # | Cause | Effect |
| --- | --- | --- |
| 1 | The builders save clock times as `ideal_start_time` / `ideal_end_time`. Kairos v2 reads only `start_time` / `start`. | Anchors, windows and timed blocks arrive with no time. With no timed sleep anchor the sleep boundary falls back to `24h - target sleep` = 16:00 (since 2026-11-18 the plan runs to 23:59 instead; `docs/scheduling/sleep_after_midnight.md`). |
| 2 | `_collect_structural_sequence` skips every fixed-time node, but `populate_day_and_windows` discovers fixed-time nodes only in `sequence`. The builders write to `children`. | A timed routine under `children` is skipped by one stage and never picked up by the other. |
| 3 | `_coerce_minutes` accepts `45` and `1h` but not `15m`, `90 min` or `1h30m`. | Every item with a duration in the documented format has no length, so windows and gaps stay empty. |
| 4 | Files created from `*_defaults.yml` have `Name:` / `Duration:`. `_iter_schedulable_library_items` reads raw keys and matches on `name`. | A routine made in the Routine Builder is never resolved, so its children are not expanded. Day templates fall back to the file stem as their name. |
| 5 | `sleep_gate.py` uses `os` without importing it. | `today reschedule` fails with `name 'os' is not defined` whenever a day template has no lowercase `name`. |

## What the prototype changes

All in `modules/scheduler/`.

- `v1.py`: three helpers.
  - `normalize_template_times(node)` fills `start_time` / `end_time` from `start` / `end` / `ideal_*` when they are missing, recursively. Explicit values win.
  - `lowercase_top_level_keys(payload)` gives the same view `ItemManager.read_item_data` gives.
  - `prepare_day_template(template)` applies both.
- `kairos_v2.py`
  - Day templates and library items pass through those helpers when read. The `read_template` call sites keep their name, so tests that monkeypatch it still work.
  - `_discover_fixed_time_structure_nodes` runs over `children + sequence`.
  - `_coerce_minutes` also accepts `15m`, `90 min`, `1h30m`, `2h 15m`.
- `sleep_gate.py`: imports `os`, and reads day templates through `prepare_day_template`.

Two behaviour changes go beyond input handling. Both exist to stop the same thing appearing twice, and both are the parts most worth your judgement.

1. **A container placed as one unit covers its members.** `_identities_covered_by_structure` removes from the viable candidates:
   - every active fixed-time node (it has its own slot, so windows and gap fill must not also take it);
   - every member of a routine / subroutine / microroutine that holds an active fixed slot, or is itself a viable candidate with a positive duration;
   - every member of a container the pilot completed or skipped today.

   Containers with no usable duration are left alone, so their members are still placed one by one in authored order. The result is recorded in `day_population.covered_by_structure` with a reason per identity.

   Before this, a day with `Morning Routine` 07:45 containing `Stretch` scheduled the routine and then `Stretch` again as a recurring habit.

2. **Skipped items are not re-queued the same day.** `remove_reality_impossible_candidates` now drops names skipped today (`impossible_reason: skipped_today`), as it already did for completed ones. `scheduling_algorithm_overview.md` step 3 says "Remove completed/skipped rows"; v2 only removed completed.

## Result on the same data

```
15:30 - 16:00  Gap Fill
                 Morning Routine (missed at 07:45, re-queued as one unit)
                 Take out trash
16:00 - 17:30  Admin            window, filters: {tags: [admin]}
                 Call the bank
                 Reply to landlord
                 Order dumbbells
17:30 - 18:30  Due Window
                 Write project report
19:00 - 19:45  Dinner           anchor
21:30 - 22:00  Evening Wind Down fixed-time routine
```

Sleep boundary: 23:30, from the sleep anchor.

## Tests

`tests/test_kairos_v2_builder_templates.py`, 12 tests on the existing `temporary_kairos_user_fixture`: duration formats, time normalisation, the builder-shaped day (template name, sleep boundary, anchor time, timed child, tag-filtered window, no duplicate member), skipped items, members of a closed routine, members of an open untimed routine.

Full suite, excluding `tests/test_kairos.py` (the archived v1 scheduler raises on import): 184 passed, 3 failed. The same 3 fail on `07a2bf1`:

- `test_console_plugins.py::test_plugin_command_and_alias_load`
- `test_timer_break_buffer_behavior.py::test_timer_build_schedule_plan_marks_break_subtype_as_buffer`
- `test_trick_debug_console.py::test_registry_includes_debug_console`

## Open questions

- **Field names.** The prototype makes Kairos accept what the builders write. The alternative is to make the builders write `start_time` / `end_time`. Normalising on read also covers templates that already exist on disk.
- **Missed timed routines.** A routine whose slot has passed is re-queued into the next gap as a unit. A morning routine at 15:30 is questionable; a per-item "do not re-queue after HH:MM" or "only before noon" property would settle it.
- **Unit versus steps.** A routine placed as a unit shows as one block with no children, so the Timer and the Home view cannot show "now: Brush teeth". Giving fixed-time and unit blocks their children laid out inside the slot is the natural next step.
- **Tasks with no due date.** `build_candidate_universe` admits only recurring items and items with a due date or deadline. A task with neither never reaches a window, even one whose tag filter matches it. `task_defaults.yml` sets `Due_Date: {{tomorrow}}`, so tasks made with `new` are covered; tasks written another way are not.
- **Zero durations.** `generic_handle_new` sets `duration: 0`, and the Brain Dump wizard has no duration field, so its tasks can never be placed. The Home view warns and offers "Give them 30 min"; a default in `task_defaults.yml` or a field in the wizard would fix it at the source.
- **Template choice.** With several eligible day templates and no status requirements, the first by name wins.

## Other fixes on the branch

Found while testing the same data set; each is separate from the scheduler.

| File | Fix |
| --- | --- |
| `commands/new.py` | `properties` passed by the console or `/api/item` were ignored, so `new task X duration:30m priority:high` saved neither. |
| `commands/set.py` | `set <type> <name> key:value` from the console always answered "No properties specified to set": `parse_input` hands `set` raw args and the command read only `properties`. |
| `commands/mark.py` | `mark "Name":status` from the console failed with "No colon found": the console had already split the token into `properties`. |
| `commands/today.py` | `today` (view) crashed with `'str' object has no attribute 'get'` on the v2 runtime payload. |
| `modules/item_manager.py` | `tags` are always written as a list (Kairos iterates them; a string was read per character). Added `{{today}}` and `{{end_of_year}}` placeholders; `milestone_defaults.yml` uses the latter. Shared `property_matches` so filters match list values. |
| `modules/console.py` | `key:[a,b]` is coerced to a list, as the docs describe. |
| `commands/list.py`, `commands/for.py`, `modules/task/main.py`, `modules/note/main.py` | Filters match list-valued properties. `find` looked up `Name` / `Content` and matched nothing. |
| `utilities/dashboard/server.py` | `_list_playlists` recursed forever with no MP3s (HTTP 500 on every dashboard load). |
| `utilities/dashboard/app.js` | The `widget:show` listener used an undefined `context`, so it was never registered and no `ChronosBus.emit('widget:show', ...)` opened anything. |
| `utilities/dashboard/views/cockpit/index.js` | Panels were imported by their pre-rename folder names; four returned 404. |
| `utilities/dashboard/views/canvas/index.js` | Saving a board parsed the YAML reply of `POST /api/item` as JSON and reported failure. |
