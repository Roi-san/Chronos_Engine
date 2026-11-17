# Status-aware scale-down: design

Status (branch `home-hub-fixes`): design confirmed by the pilot on 2026-11-17. **All three steps implemented**: 1) flexible items, 2) fixed template slots, 3) Home. See the [implementation log](#implementation-log) and [future ideas](#future-ideas).

Related: `docs/scheduling/direction_goals_commitments.md` (goal and commitment pressure, the existing lighter-version swap), `docs/reference/item_properties.md` (what Kairos reads today).

## Why

How you feel today (health, energy, focus, ...) is meant to shape the plan. In Kairos v2 it barely does: an item whose `status_requirements` do not fit today is still placed, unless a lighter version (`mini_of`) exists. A sick day plans like any other day.

The guiding principle, from the pilot (2026-11-17): Chronos exists to **help** you get things done. It must be forgiving by default and never punish; it is strict only where you choose strictness. When in doubt, keep things visible rather than hidden.

## What Kairos does today (measured)

Each case was run through Kairos v2 with the shipped status setup (Health rank 1, Place 2, Energy 3; the shipped value scales). "Gym" is a 60-minute daily habit; "Mobility" is its lighter version (`mini_of: Gym`).

| Case | Today's result | Right? |
| --- | --- | --- |
| No requirements, sick day | Gym | yes |
| Needs energy high, no lighter version, sick day | **Gym** | no: nothing lightens the day |
| Needs energy high + lighter version, sick day | Mobility | yes |
| Needs energy high + lighter version, good day | Gym | yes |
| **Needs energy medium + lighter version, high-energy day** | **Mobility** | **no: a better day than needed gets the lighter version** |
| **A low-energy item (`energy: low`) + lighter version, high-energy day** | **Mobility** | **no: same bug** |
| Lighter version also does not fit (mini needs medium, today low) | Mobility | yes (keep the smaller one visible) |
| Sick day, commitment at its last chance, no lighter version | Gym | yes (urgent) |
| Task due today needing energy high, sick, no lighter version | Gym | yes (urgent) |
| Fixed 18:00 slot in the day template needing energy high, sick | Gym | no: should become the lighter version |
| Status never set / misspelled value / dimension not in `status_settings.yml` | Gym | yes (ignored safely) |

Root cause of both bugs: the fit is measured as a **two-way distance**. Being better than an item needs counts as a mismatch, the same as being worse.

## How status importance works today (verified)

Status dimensions have **no numeric weight**. `user/settings/status_settings.yml` gives each dimension a `Name` and a `Rank` (1 = most important), and Kairos v2 reads only those two fields (`KairosV2Scheduler._normalize_status_dimensions`). It turns rank into a weight: with N dimensions, weight = N + 1 - rank (shipped: Health 7, Place 6, Energy 5, Mind State 4, Focus 3, Emotion 2, Vibe 1). The onboarding wizard writes `Rank` in list order; the Status Mapping wizard sorts by it. No wizard or widget writes a weight. The archived v1 scheduler had a "Status Alignment" row in `scheduling_priorities_legacy.yml`; v2's `scheduling_priorities.yml` has none.

The 0-10 weights a pilot can set are in `scheduling_priorities.yml` (Category, Happiness, Due Date, Deadline, Priority Property, Goal Alignment, Commitment Pressure). This design uses Goal Alignment and Commitment Pressure.

Each dimension's values are ordered in `user/settings/<dimension>_settings.yml` by a `value` number, 1 = best (Health: Excellent 1 ... Critical 5; Energy: High 1 ... Exhausted 4). Every shipped dimension except Place runs this way. Place is a list of locations, not a scale; Kairos v2 ignores it in status fit and this design keeps it that way.

## Decisions so far

| # | Question | Decision |
| --- | --- | --- |
| 1 | How is "fit" measured for an item? | One-way. A dimension falls short when today is worse than the worst value the item accepts. Better than needed is never a mismatch. (Template choice keeps the two-way closest match, so a "Sick Day" template does not win on a healthy day.) |
| 2 | One step short? | One step of **grace**: an item is only left out when today is 2 or more steps short. |
| 3 | Short, and a lighter version exists? | Swap to the lighter version as soon as today is short at all (1+ steps). |
| 4 | Neither version fits? | Keep the smaller one in the plan. Seeing it and skipping it beats not seeing it. |
| 5 | Urgent items with no lighter version? | Stay. Urgent = due date or deadline today or overdue, or a commitment at "last chance" or "behind". Goals alone are never urgent. |
| 6 | Anchors and appointments? | Never touched by status. |
| 7 | Fixed slots in the day template? | Keep the time, swap the content to the lighter version ("gym at 6, push-ups at home"). Moving it to a later free slot is wanted but deferred: Kairos cannot do it reliably yet. |
| 8 | Far short (2+ steps), no lighter version, not urgent? | Not in the schedule, **unless its importance to you outweighs the strain** (see below). Listed on Home as "Saved for a better day" with an Add back button. |
| 9 | User controls? | Grace per dimension and per item. Weights stay rank-based for now, behind one function, so numeric weights can be added later (see "Adding weights later"). The pilot wants real weights eventually: importance differs between people. |
| 10 | Does an item's own `priority` count as importance? | Yes: critical / urgent / highest 1.0, high 0.7, medium / normal / moderate 0.4, times the Priority Property weight / 5. |
| 11 | Close calls? | Lean toward keeping: kept when importance >= strain - 0.1. |
| 12 | Order of work | 1) flexible items, 2) fixed template slots, 3) Home. Check in with the pilot after each. |
| 13 | A fixed slot with no lighter version that is saved? | Free the time, so other work that suits the day, or goals and commitments that are behind, can use it (pilot, 2026-11-17). |

## Proposed rule

For each item with `status_requirements`, for each dimension it names (declared in `status_settings.yml`, values known):

- `short` = how many steps today is below the worst value the item accepts (0 if it fits).
- `beyond` = `short` minus that dimension's grace (never below 0).

Then:

1. Nothing short: schedule the item.
2. Short and a lighter version exists: schedule the lighter version (decision 3), even if it is short too (decision 4).
3. No lighter version, nothing beyond grace: schedule the item.
4. No lighter version, beyond grace:
   - urgent: schedule it, with the note "urgent, kept although ...".
   - otherwise compare **importance** with **strain**: schedule it if importance >= strain - 0.1 ("kept: <goal> matters more than low energy today"), else save it for a better day.

Items added by hand (manual injections) and items that fit are never touched. A lighter version that is more demanding than the full one (a larger one-way distance) is not used.

**Strain** = sum over dimensions of `beyond x dimension weight`, where dimension weight is 0-1: the top-ranked dimension is 1, then it falls by rank (weight = (N + 1 - rank) / N). Shipped: Health 1.0, Place 0.86, Energy 0.71, Mind State 0.57, Focus 0.43, Emotion 0.29, Vibe 0.14.

**Importance** = the strongest of the item's goal pressure, commitment pressure and own `priority`, each times its 0-10 weight from `scheduling_priorities.yml` divided by 5 (Goal Alignment, Commitment Pressure, Priority Property; 5 is neutral, 10 doubles, 0 switches it off, a missing row counts as 5). Pressure levels are the existing ones in `direction.py` (commitment: on track 0.2, tightening 0.45, at risk 0.7, last chance 1.0; goal: 0.35 x priority weight + closeness). Priority: critical 1.0, high 0.7, medium 0.4.

Worked examples with the shipped settings (grace 1; Goal Alignment 5, Commitment Pressure 5, **Priority Property 4**):

| Item needs | Today | Strain | Importance | Result |
| --- | --- | --- | --- | --- |
| energy high | medium | 0 | | scheduled (within grace) |
| energy high | low | 0.71 | none | saved for a better day |
| energy high | low | 0.71 | commitment at risk 0.70 | kept (close call, within 0.1) |
| energy high | low | 0.71 | high-priority goal due in 2 days 0.90 | kept |
| energy high | low | 0.71 | `priority: critical` 1.0 x 4/5 = 0.80 | kept |
| energy high | low | 0.71 | `priority: high` 0.7 x 4/5 = 0.56 | **saved** (Priority Property 5 would keep it: 0.70) |
| energy high | exhausted | 1.43 | high-priority goal due in 2 days 0.90 | saved |
| health good | poor | 1.00 | high-priority goal due today 1.00 | kept |
| health good + energy high | Sick day (poor, low) | 1.71 | at-risk commitment 0.70 | saved |
| anything | anything | | commitment last chance / due today | kept (urgent) |

## User controls

- **Per dimension**: an optional `Grace` on a row of `status_settings.yml`, in steps (default 1). `Grace: 0` makes that dimension strict, `Grace: 2` loose.
- **Per item**: optional `status_grace: <steps>` overrides the grace for that item on every dimension.
- **Importance**: the existing Goal Alignment and Commitment Pressure weights in `scheduling_priorities.yml`.
- **Add back**: Home's button runs `today inject "<name>" type:<type>`. Anything you add by hand is never removed by status.

## Adding weights later

All dimension importance comes from one place: `KairosV2Scheduler._normalize_status_dimensions`, which returns each dimension's `weight`. Today it is derived from `Rank`. To make it user-set:

1. Add an optional `Weight: 0-10` to rows in `status_settings.yml`.
2. In `_normalize_status_dimensions`, use `Weight` when present, else the rank-derived value, and expose both a raw weight (for template choice, which compares relative distances) and a 0-1 weight (for strain).
3. Let the Status Mapping wizard and the Settings widget write `Weight`.
4. Re-check the worked examples above; strain scales directly with the weight.

Until then, the order of dimensions in `status_settings.yml` is how importance is expressed.

## Where results show

- `schedule.reality_filtered_candidates.impossible_candidates`, reason `saved_for_better_day`, with each short dimension (needed, today, steps), strain and importance.
- Kept-despite and urgent cases: a `status_note` on the candidate.
- Home (step 3): a "Saved for a better day" card with Add back; the "Lighter version of ..." note (now also for fixed-slot swaps); a "Kept although ..." sentence on kept blocks, with a **tough today** tag in the Today list. Wording is built in `utilities/dashboard/home_api.py` (`status_effects`).

## Future ideas

Raised by the pilot, not built:

- **Fill freed time with what suits the day.** A slot freed by status (or any gap) should go to work that fits today's mood and energy, or to goals and commitments that are falling behind. What exists: freed time becomes an ordinary gap; gap fill ranks by score, which includes goal and commitment pressure (so work behind on a commitment is preferred, and helper windows open for strong pressure), and items that do not fit today were already swapped or saved. What is missing: a positive preference for items that *suit* today (for example items authored for low energy on a low day get no bonus; fit only ever subtracts).
- **Move a slot instead of shrinking it** (decision 7): if the full version cannot happen at its time but a later free, un-anchored time exists, offer it there.
- **Numeric status weights**: see "Adding weights later".
- **A penalty or trigger when a commitment period ends unmet** (`direction_goals_commitments.md`, "Rewards and consequences today").

## Not in this change

- Moving a fixed slot to a later free time (decision 7, deferred; see Future ideas).
- Steps inside a routine placed as one block are not checked one by one.
- Numeric status weights (see above).
- Place.
- The Today widget's "status threshold" box sends `status_match_threshold`, which Kairos v2 never reads. Left as is.

## Open questions

None for step 1. Resolved: priority counts (decision 10), close calls keep (decision 11), order of work (decision 12).

To revisit with real use:

- Shortfalls do not add up within grace: an item one step short on two dimensions at once stays (each is within its own grace). Strain only adds up what is beyond grace.
- With the shipped Priority Property weight of 4, `priority: high` does not keep an item on a low-energy day (0.56 vs 0.71).
- A deadline tomorrow is not urgent today, so on a far-short day such an item is saved today and kept (urgent) tomorrow.

## Implementation log

### Step 1: flexible items (2026-11-17)

Prerequisite, own commit `30ea006`: a 0 weight in `scheduling_priorities.yml` did not switch a factor off (`_priority_factor_weights` dropped rank-0 rows, so callers used their default). Importance depends on these weights.

Code, all in `modules/scheduler/kairos_v2.py`:

| Where | Change |
| --- | --- |
| module constants | `STATUS_DEFAULT_GRACE = 1`, `STATUS_CLOSE_CALL_MARGIN = 0.1`, `STATUS_PRIORITY_IMPORTANCE`, `STATUS_URGENT_COMMITMENT_STATES`. Every tunable number is here. |
| `_normalize_status_dimensions` | Also returns `grace` (from an optional `Grace` on the row) and `unit_weight` (0-1). Template choice reads only `weight`, which is unchanged. |
| `_coerce_status_grace` | New: reads a grace value (int >= 0, else "not set"). |
| `_score_status_shortfall` | New: the one-way fit. Returns `weighted_distance` (same scale as before, but one-way), `strain`, `short_dimensions`, `max_short`, `max_beyond_grace`. Case-insensitive keys; place and unknown values skipped. |
| `_attach_candidate_status_fit` | Uses `_score_status_shortfall` instead of the two-way `_score_status_requirements_alignment`, with the item's `status_grace`. Its consumers (scale-down, cut order in `_score_preservation_value`, `inject:next` in `_score_asap_next_candidate`) therefore see one-way distances. |
| `_normalize_candidate` | Carries `status_grace`. |
| `_scale_down_for_status` | Rewritten per-candidate part: manual injections and fitting items untouched; usable lighter version (not more demanding) swapped in even if short; otherwise `_status_unfit_verdict`. Returns kept, swaps, saved, kept-notes. The duplicate-mini pass after it is unchanged. |
| `_status_unfit_verdict`, `_status_urgency_reason`, `_status_importance` | New: the rule above. |
| `remove_reality_impossible_candidates` | Adds saved items to `impossible_candidates` (reason `saved_for_better_day`, with `status_verdict`), writes `schedule.status_scale_down` and three lists in its phase notes. |

Unchanged on purpose: template selection (`_score_template_status_alignment`), anchors, fixed-time template structure (step 2), everything for items without `status_requirements`.

Tests: `tests/test_kairos_v2_status_scale_down.py`, 37 tests, one class per decision. Written before the code: 20 failed, 17 passed (safe defaults and behaviour that was already right). After: 37 passed. Existing scale-down and direction tests unchanged and passing.

Verification:

- Full suite: 255 passed; the same 2 failures as untouched upstream (timer break-as-buffer, TRICK debug-console registry).
- Scenario table (the "What Kairos does today" cases), before and after: only the intended rows changed. Needs energy high with no lighter version on a sick day: Gym -> saved. Needs medium + lighter version on a high-energy day, and a low-energy item + lighter version on a high-energy day: Mobility -> Gym (bug fixed). The fixed-slot row is unchanged (step 2).
- 7-day rich fake-life plan (no status changes across days): identical before and after.
- 7-day status-heavy week (good, medium, low, sick, exhausted, excellent, no status; items with and without requirements, lighter versions, goal, deadline, a low-energy item): items without requirements are placed on exactly the same days before and after; the only removals are items with requirements, each with the reason the rule gives (Wednesday: File taxes saved, deadline tomorrow; Friday exhausted: Long run, Deep refactor, Write launch post saved; Thursday: File taxes kept as urgent).
- The pilot's real data has no `status_requirements` yet, so nothing changes for them until they author some.

Committed as `4b2c818`.

### Step 2: fixed template slots (2026-11-17)

Problem found while writing the tests: a fixed slot ("Gym 18:00", a direct child of the day template) is also a flexible candidate, so step 1 (and the lighter-version swap before it) already swapped it in the candidate list. The slot itself stayed: the plan showed Gym at 18:00 **and** Mobility in some gap (08:10). Present since lighter-version swaps were added on `home-hub`.

Code, all in `modules/scheduler/kairos_v2.py`:

| Where | Change |
| --- | --- |
| `KairosV2RunState.direction_by_identity` | New field: goal/commitment signals, filled in `build_candidate_universe`, so later phases can use them. |
| `populate_day_and_windows` | Runs `_scale_down_fixed_time_nodes` on the active fixed-time list right after it is built, before every reader (covered-by-structure, `_derive_emergent_gaps`, `place_remaining_structure`, `_build_conceptual_blocks`). |
| `_scale_down_fixed_time_nodes` | New. Per slot, the step-1 rule with the step-1 functions (`_attach_candidate_status_fit`, `_resolve_authored_mini_variant`, `_status_unfit_verdict`): unchanged if it fits / has no requirements / was completed or skipped today; lighter version takes the slot at the same start for its own length (capped at the slot); kept with `status_note`; or removed (saved), which leaves a gap. |
| `_note_fixed_slot_status` | New. Records the decision with `fixed_slot` ("HH:MM-HH:MM") in `schedule.status_scale_down`, merged into the step-1 row of the same item; a saved slot whose item was not a candidate is also added to `impossible_candidates`. Phase notes: `fixed_slot_status_scale_down`. |

Why the duplicate disappears: the lighter version is now itself a fixed slot, so the existing covered-by-structure pass removes its flexible copy.

Tests: `tests/test_kairos_v2_status_fixed_slots.py`, 14 tests. Written before the code: 7 failed (swap in place, own length, no duplicate, requirement on the slot, record, freed slot, freed time is a gap), 7 passed. After: 14 passed.

Verification:

- Full suite: 269 passed; the same 2 pre-existing failures.
- Scenario table: only the fixed-slot row changed (sick day, slot needs energy high, no lighter version: Gym -> freed).
- Rich 7-day plan and the status-heavy week (no fixed slots with requirements): identical to step 1.
- A fixed-slot week (Deep work 09:00-11:00 needing focus, Gym 18:00 needing health and energy, with a lighter version; goal, commitment and plain tasks): Wednesday and Thursday changed from "Gym 18:00 + Mobility 08:00" to "Mobility 18:00-18:20"; Friday (focus absent) freed Deep work's 09:00-11:00; Monday (good day) unchanged.

Committed as `9c7da21`.

### Step 3: Home (2026-11-17)

What the pilot sees:

- **Saved for a better day** card (only when something was saved): name, the fixed slot's time if it was one, and what today falls short on ("Today energy is exhausted (needs high)."). **Add back** runs `today inject "<name>" type:<type>` through `window.ChronosRunCliCommand` (so the sleep prompt still works), which re-plans; the note then says where it went ("Added back: Gym at 22:30.") or that no time was left.
- **Kept although ...**: a sentence per kept block, in Right now's reasons and in the Today list's tooltip, with a **tough today** tag. Reasons: "it is only a little short" (grace), "its deadline is today" / "it is due today" / "it is overdue" / "its deadline has passed" / "it is the last chance to keep its commitment" / "its commitment is behind" (urgent), "its goal/commitment/priority matters more than the strain" (importance, strongest source named).
- **Lighter version of ...** now also appears for fixed-slot swaps (step 2 records them only in `status_scale_down.swapped`; Home merges both records).

Problem found while writing the tests: Add back did not work for a fixed slot. The slot pass (`_scale_down_fixed_time_nodes`) did not look at manual injections, so a saved "Gym 18:00" stayed removed and the injected copy went to the first free gap (08:00) instead. Fixed: a slot whose item has a soft manual injection today is left as authored (`notes.added_back`). A hard injection (`today inject X at HH:MM`) is not treated this way, since it has its own time.

Code:

| Where | Change |
| --- | --- |
| `kairos_v2._scale_down_fixed_time_nodes` | Skips slots added back by hand (soft injections), recorded in phase notes `fixed_slot_status_scale_down.added_back`. |
| `home_api.status_effects` (new) and helpers | Turns `schedule.status_scale_down` into `today.status_effects` = `{saved: [{name, type, fixed_slot, text}], kept: {name: sentence}}`. Type comes from the identity (`habit:gym`), default `task` like `today inject`. Malformed input gives empty lists. |
| `home_api._today` | Adds `status_effects`; drops saved items already on the plan or done today; merges fixed-slot swaps into `scaled_down`. |
| `views/home/index.js` | `renderSaved` card, `addBack` action, kept sentence in `blockReasons`, **tough today** tag. |

Tests: 2 new in `tests/test_kairos_v2_status_fixed_slots.py` (added back returns to its own slot; is not swapped for the lighter version), written first, both failed (Gym at 08:00), now pass. 16 in `tests/test_home_api_status_effects.py` (wording, malformed input, dedup, and 4 against real Kairos plans so a change to the record's shape breaks them).

Verification:

- Full suite: 287 passed; the same 2 pre-existing failures.
- End to end in a throwaway copy, real CLI and dashboard in headless Chrome: exhausted evening with a fixed "Gym 22:30" slot (needs energy high), a daily "Long run" (needs high) and "File taxes" (deadline today, needs medium + good health). Home showed Gym (22:30 - 23:15) and Long run as saved, File taxes as **tough today** with "its deadline is today". Pressing Add back on Gym: "Added back: Gym at 22:30.", Gym back at 22:30 - 23:15, Long run still listed. No new console errors (only the known 404s for the avatar and the generated settings bundle).

Noticed, not caused by this change, not fixed (tracked in `docs/ISSUES_AND_NEXT_STEPS.md`):

- **Sleep after midnight empties the day.** A sleep anchor at `00:30` is read as 00:30 *this* morning, so `remaining_minutes_before_sleep` is 0 and nothing is placed. Sleep at 23:55 works.
- **Work is placed after a fixed slot rather than before it.** At 22:05 with Gym fixed at 22:30, File taxes (20 min) goes to 23:15 after a re-plan, although 22:07 - 22:27 is free. Same with no status involved at all.
- **`python modules/console.py today reschedule` segfaults on exit** when its output is redirected (exit 139). The schedule is written first. Same on the untouched previous commit; not seen from the dashboard.
