# Items without a length (decision D1)

Status (branch `home-hub-fixes`, 2026-11-18): **implemented**, code committed in `969cabb`. Fixes issue 12 in `docs/ISSUES_AND_NEXT_STEPS.md` (roadmap step 1a, `docs/ROADMAP.md`).
Code: `modules/scheduler/kairos_v2.py` (`_effective_length`, `_known_length`, `_default_item_minutes`, `_fill_structure_length`, `_normalize_candidate`), `utilities/dashboard/home_api.py` (`length_notes`), `utilities/dashboard/views/home/index.js`, `utilities/dashboard/wizards/brain_dump/index.js`, `user/settings/scheduling_settings.yml`.
Tests: `tests/test_kairos_v2_item_lengths.py`, `tests/test_home_api_item_lengths.py`.

## The problem

Kairos cannot place a 0-minute item, and it checks for a positive length in seven places. Before this change:

- `new task ...` without a length writes `duration: 0` (`modules/item_manager.py`), the Brain Dump wizard had no length field, and the Chore Setup wizard writes `duration: 0` when its minutes box is left empty. All of these items were never planned. Home only warned.
- **A routine without a length of its own disappeared from the plan, steps and all.** Measured with a probe (`routine_probe.py`, fixture day, 08:00):

| Case | Before |
| --- | --- |
| A. Routine without a length, steps 5 + 15 + 10 min | nothing planned |
| B. Routine with its own length (20 min), same steps | one 20-minute block (the steps' 30 minutes are covered by it) |
| C. Routine without a length, steps without lengths | nothing planned |
| D. Routine from the library (`frequency: daily`), no length, steps 5 + 15 + 10 | nothing planned |

The code comment said such routines' steps are "still placed one by one"; only steps that were in scope by themselves (for example a task with a due date) were, and then scattered apart.

## Decisions (pilot, 2026-11-18)

| # | Question | Decision |
| --- | --- | --- |
| 1 | An item without a length | Planned for a default length, a global setting, 30 minutes when not set. |
| 2 | Where to give a length | The Brain Dump wizard gets a length field (Home's quick capture already asks for one). |
| 3 | Routines | "A placeholder for the things that live inside it", taken into account with its possible length: a routine without its own length is planned as one block for the total of its steps. Whole routines are never left out. |

Implementation choices, not asked (all forgiving, all visible):

- **An item's own length always wins.** A routine with its own length keeps it even when its steps add up to more (case B is unchanged).
- **Only known step lengths count.** A step without a length adds 0 to its routine's total.
- **A routine none of whose steps has a length gets the default once**, for the whole routine. Giving every step the default would make five unsized steps 2.5 hours.
- **Start and end times count as a length.** A block authored from 07:00 to 07:20 is 20 minutes, not the default.
- **Left alone:** anchors, sleep blocks, windows, timeblocks (free, buffer, break, ...). Only tasks, habits (chores are habits), routines, subroutines and microroutines get lengths this way.

## The rule

`_effective_length(node)` gives (minutes, source):

| Node | Length | `source` |
| --- | --- | --- |
| Has a positive `duration`, or a start and an end time | that | `own` |
| Routine / subroutine / microroutine without one, steps with known lengths | the total of its steps' known lengths (steps are read from their own files when the routine only names them; nested routines add up) | `steps` |
| Routine none of whose steps has a length | `default_duration_minutes` | `default` |
| Task or habit without one (`duration: 0` counts as none) | `default_duration_minutes` | `default` |
| Anything else | unchanged | none |

It is used in exactly two places that both see the same answer:

1. **`_normalize_candidate`**, which every candidate passes through: template children, library items, items added by hand (Add back), lighter versions, fixed slots.
2. **`_fill_structure_length`**, on the top-level nodes of the day's structure before fixed-time slots are found, so "Gym at 18:00" with no length keeps its 18:00 slot (for 30 minutes) instead of vanishing.

The setting, in `user/settings/scheduling_settings.yml`:

```yaml
default_duration_minutes: 30
```

## What you see

- **Home, Today list:** a block planned with the default length is tagged **no length**; its tooltip and "Right now" say "No length set, so Chronos planned 30 min. Set its real length in Manage." A routine planned from its steps says "Planned for 25 min, the total of its steps."
- **Home, Tasks card:** "N of these have no length yet, so Chronos plans them as 30 min. Set real lengths in Manage." (It used to say Chronos cannot place them.) The "Give them 30 min" button still writes a real 30-minute length.
- **Brain Dump, Refine step:** a Length field per task (minutes; empty means the default).
- **Decision log and schedule file:** `schedule.assumed_lengths` lists every assumed length with its source; the phase notes of `build_candidate_universe` list them too.

## What changed

| Where | Change |
| --- | --- |
| `kairos_v2.py` constants | `DEFAULT_ITEM_MINUTES = 30`, `LENGTH_LEAF_TYPES`, `LENGTH_CONTAINER_TYPES`. |
| `kairos_v2._effective_length`, `_known_length`, `_default_item_minutes` | New: the rule above; the default is read from `scheduling_settings.yml` once per run. |
| `kairos_v2._normalize_candidate` | Uses the rule; candidates carry `duration_source`. |
| `kairos_v2._fill_structure_length` | New; run in `populate_day_and_windows` right after the structure is expanded. |
| `kairos_v2.build_candidate_universe` | Writes `schedule.assumed_lengths` and a phase note. |
| `home_api.length_notes`, `_default_item_minutes`, `_today`, `build_summary` | Sentences for Home, the default for the Tasks card (`defaults.item_minutes`). |
| `views/home/index.js` | Length sentence in a block's reasons, the **no length** tag, the Tasks card wording. |
| `wizards/brain_dump/index.js` | Length field (and its dark styling); saved as `duration` when given. |
| `user/settings/scheduling_settings.yml` | The setting, with comments on what Kairos v2 reads; the old pre-Kairos examples are marked as such. |
| `tests/test_kairos_v2_builder_templates.py` | `test_members_of_an_open_untimed_routine_are_still_scheduled` became `test_an_open_untimed_routine_is_planned_whole_with_its_steps`: the routine is now one block of its steps' total and its step is covered by it (intended change, decision 3). |

## Tests

- `tests/test_kairos_v2_item_lengths.py`, 16 tests, written before the code: **13 failed, 3 passed**. Two are controls (an item's own length is kept, for a task and a routine); the third ("its steps are not planned a second time") passed only because nothing was planned at all. After: 16 passed.
- `tests/test_home_api_item_lengths.py`, 4 tests (wording, malformed input, a real Kairos plan): all failed before (no `length_notes`), pass after.
- One existing test changed on purpose (above).

## Verification

- **Full suite** (fresh export): **365 passed, 0 failed** (345 before, plus 20 new).
- **Fake-life regression dumps** (`rich_dump`, `status_week`, `status_matrix`, `fixed_week`, `plan_dump`, and the two with breathing room on): **identical** before and after. Every item in those fake lives has a length, so nothing changes for them.
- **End to end**, throwaway export, real commands at 21:33: `new task "Call the bank e2e" due_date:<today>` wrote `duration: 0`; a day template held an "Evening Routine" with no length and two steps (10 and 15 min); `today reschedule` exited cleanly. Planned: Call the bank e2e 21:33-22:03 (30 min, default), Evening Routine 22:08-22:33 (25 min, its steps), with breathing room between. Home's summary had both sentences and tagged the task; the timer's plan had both blocks with those lengths.
- **In a real browser** (headless Chrome, the dashboard on a throwaway copy): Home showed "Call the bank e2e" with the **no length** tag; Brain Dump's Refine step showed a Length field per task; creating two tasks saved one with `duration: 20` and the other without a length. Only the two known harmless 404s (issue 7).

## Limits

- **An anchored routine without a length** (`reschedule: never`) is committed before lengths are filled, so it still needs its own length or an end time.
- **Steps inside a routine** get no length of their own; they are covered by their routine's block. Home and the timer show the routine as one block (issue 15 is about laying the steps out inside it).
- **A routine whose own length is shorter than its steps' total** keeps its own length; nothing flags the difference yet.
- `new` still writes `duration: 0`; Kairos treats it as no length. Other creators (wizards, an AI) are covered the same way.
- A timed step inside a routine with a start but no length is not given one.
