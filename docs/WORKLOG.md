# Work log

Every change made on the `home-hub` and `home-hub-fixes` branches, oldest first: what was wrong, what changed, where, how it was checked, and where the details are. It exists so that a person or a new AI session can catch up without the chat history.

- New here? Read `docs/START_HERE.md` first.
- Add an entry with every commit, at the bottom. Keep the format: why, changed, checked, details. Name files and functions so they can be searched.
- The tracker (`docs/ISSUES_AND_NEXT_STEPS.md`) says what is open; the roadmap (`docs/ROADMAP.md`) says in what order. This log says what happened.

## Before the first commit (2026-11-15 and 2026-11-16)

- **2026-11-15.** An earlier session rebuilt the dashboard on an outdated copy and stripped it down to a to-do page. The pilot rejected it: Chronos is a "life engine" where you load goals, commitments, routines and habits once and it plans around your state. Lessons that still apply: add, do not remove (keep every wizard, builder and widget); always `git fetch` and compare with `origin` before starting, because an outdated copy was handed over twice.
- **2026-11-16.** The local `main` was stale (1 March 2026); the newest upstream is `alpha_v0.3` (`07a2bf1`, 2026-04-17). Branch `home-hub` was cut from it. The pilot asked for Chronos to be bug-free for their own use (not power-user complete), allowed real changes to the scheduler as a prototype for the friend to review, and had the alpha gate unlocked (`user/settings/alpha_gate_settings.yml`) so goals, commitments and projects work.

## 2026-11-17 00:45 · `f44cd71` · Home page, builder-made days, about fifteen bug fixes

- **Why.** The dashboard had no landing page. A day built in the Day Builder, Routine Builder or Life Setup wizard came out of Kairos almost empty (five independent causes). Many console commands were broken.
- **Changed.**
  - Home view: `utilities/dashboard/views/home/`, read-only `GET /api/home/summary` in `utilities/dashboard/home_api.py`. Right now, today's plan, status check-in, quick capture with `#tags`, a setup checklist, one card per area of life.
  - Kairos v2 (`modules/scheduler/kairos_v2.py`) reads the builders' `ideal_start_time` / `ideal_end_time` (helpers `normalize_template_times`, `lowercase_top_level_keys`, `prepare_day_template` in `modules/scheduler/v1.py`), finds timed blocks under `children`, understands `15m` / `90 min` / `1h30m`, finds `Name:` files, lets a routine placed as one block cover its steps (`_identities_covered_by_structure`), and does not re-queue items skipped today. `sleep_gate.py` was missing `import os`.
  - Bug fixes: `new` ignored properties; `set` and `mark` from the console; `today` view crash; tags saved as text; `find` matched nothing; `{{end_of_year}}` literal; playlists recursion; `widget:show` listener in `app.js`; Cockpit panel paths; Canvas save.
- **Checked.** 12 new tests (`tests/test_kairos_v2_builder_templates.py`). A realistic fake life through every view, widget and wizard in a headless browser.
- **Details.** `docs/HOME_HUB_HANDOVER.md`, `docs/scheduling/builder_templates_prototype.md`, `docs/guides/home.md`.

## 2026-11-17 14:47 · `7768099` · Goals and commitments become scheduling factors

- **Why.** The pilot found Kairos ignored goals and commitments ("what's the point then").
- **Changed.** `modules/scheduler/direction.py` (new): goal pressure (priority and closeness of the date), commitment pressure (slack in the period, extra push after a missed period, interchangeable targets). Wired into `kairos_v2.py`: linked items come into scope, `_urgency_bonus` adds points, helper windows open for strong pressure. Lighter versions (`mini_of` / `mini_variant`) are swapped in when today's status does not fit; `modules/commitment/main.py` counts them. Two weight rows in `user/settings/scheduling_priorities.yml`: Goal Alignment, Commitment Pressure. Home shows the reasons.
- **Checked.** `tests/test_kairos_v2_direction.py`. Suite 205 passed, 2 failed; the third upstream failure (`test_console_plugins`) was fixed on this branch.
- **Details.** `docs/scheduling/direction_goals_commitments.md`.

## 2026-11-17 19:05 · `e6c65f5` · The habit module loads again; stale docs

- **Why.** `modules/habit/main.py` had a syntax error upstream since polarity was added, so every habit command silently fell back to the generic handlers.
- **Changed.** Fixed the module; `new`, `append` and `delete` stay on the generic handlers, because that is what had really been running. Docs and the docs-drift script corrected.
- **Lesson.** When fixing a module that never loaded, check what the fallback path was doing first, because "fixing" it reroutes callers. No habit tests existed (tracker next task 3).

## 2026-11-17 19:27 · `e01ac10` · Docs say what Kairos v2 actually reads

- **Changed.** `docs/dev/architecture.md` lists the v2 phases; `docs/reference/item_properties.md` was rewritten from real runs, including a "Not read by Kairos v2" table (`essential`, `flexible`, `depends_on`, `auto_inject`, `variants`, `environment`).

## 2026-11-17 21:13 · `9c3383f` · Finished one-off tasks stop coming back

- **Why.** A completed one-off task returned the next day as overdue.
- **Changed.** Kairos skips items without a `frequency` whose status is finished (`_is_finished_one_off`), unless a commitment needs them; `complete task` writes `status: completed` like `mark` does.
- **Checked.** `tests/test_kairos_v2_finished_tasks.py`; a 7-day before/after plan diff on a fake life.

## 2026-11-17 21:14 · `30ea006` · A weight of 0 switches a factor off

- **Why.** `_priority_factor_weights` dropped rows with rank 0, so callers fell back to their defaults.

## 2026-11-17 21:48 · `4b2c818` · Status scale-down, step 1: flexible items

- **Why.** How you feel barely shaped the plan, and a better-than-needed day got the lighter version (fit was measured both ways).
- **Changed.** One-way fit with one step of grace (`Grace` per status dimension, `status_grace` per item); a lighter version as soon as today falls short; urgent items stay; otherwise importance against strain (close calls keep); the rest is "saved for a better day". Recorded in `schedule.status_scale_down`. Functions: `_score_status_shortfall`, `_scale_down_for_status`, `_status_unfit_verdict`.
- **Checked.** 37 tests (20 failed before); suite 255 passed, 2 failed (the 2 upstream ones).
- **Details.** `docs/scheduling/status_scale_down_design.md`, decisions 1 to 13 by the pilot.

## 2026-11-17 21:57 · `9c7da21` · Status scale-down, step 2: fixed template slots

- **Changed.** A fixed slot keeps its time and takes the lighter version, or is freed (`_scale_down_fixed_time_nodes`). Fixed a duplicate: the slot stayed and its lighter version was also placed elsewhere.
- **Checked.** 14 tests; suite 269 passed, 2 failed.

## 2026-11-17 22:14 · `04bc2f0` · Status scale-down, step 3: Home; the tracker is born

- **Changed.** Home's "Saved for a better day" card with **Add back** (`today inject "<name>" type:<type>`), the **tough today** tag and "Kept although ..." sentences (`home_api.status_effects`). Add back returns a fixed slot to its own time. `docs/ISSUES_AND_NEXT_STEPS.md` created at the pilot's request: one file for open issues and next tasks.
- **Checked.** 18 tests; suite 287 passed, 2 failed; end to end in headless Chrome.

## 2026-11-18 02:52 · `d652300` · Issue 1: a bedtime after midnight emptied the day

- **Why.** The pilot's Core Sleep starts at 02:00; Kairos read it as 02:00 this morning, so every re-plan planned nothing flexible. Also: no sleep block stopped the plan at 16:00; "go back to sleep" planned nothing flexible.
- **Changed.** `model_day_budget` and `_resolve_next_bedtime`: a sleep anchor starting 00:00-11:59 is a bedtime after midnight; the plan runs to 23:59 (`PLAN_LAST_MINUTE_OF_DAY`), or to the bedtime when it is past midnight and still ahead. `_derive_emergent_gaps` honours the sleep prompt's answer.
- **Checked.** 27 tests (24 failed before); suite 314 passed, 2 failed; regression dumps identical; end to end with the real clock at 02:44.
- **Details.** `docs/scheduling/sleep_after_midnight.md` (with the "day lasts until bedtime" idea for later).

## 2026-11-18 03:22 · `7c35976` · Issue 2: urgent work takes the earliest gap; breathing room

- **Why.** Urgent work only opened helper windows in gaps of 30+ minutes, so it jumped past small gaps (a deadline task went after the gym). Kairos left no margin anywhere.
- **Changed.** `RUNTIME_HELPER_DEFAULT_MIN_GAP_MINUTES = 1`. Breathing room: `_apply_breathing_room` / `_space_items` read `buffer_settings.yml` `global_dynamic_buffer` (5 minutes) and add margins only from spare time, never changing what is planned. "Light days" (pack or spread) left as an open decision.
- **Checked.** 19 tests (13 failed before); suite 333 passed, 2 failed; two fake weeks with breathing room on plan the same items.
- **Details.** `docs/scheduling/gaps_and_breathing_room.md`.

## 2026-11-18 evening · no commit · Full review of the documentation

- All 176 files in `docs/`, the ADUC and Thoughtforms docs were read; memory notes refreshed; the pilot asked for small sure fixes and an open list.

## 2026-11-18 19:50 · `03b980e` · Issue 3: the exit crash was the "done" chime

- **Why.** `python modules/console.py today reschedule` exited with 139 after saving the schedule. `python -X faulthandler` put the crash in `modules/sound_fx.py` `_play_sync`, on a daemon thread still inside pygame while Python shut down.
- **Changed.** The chime thread is no longer a daemon (Python waits for it before exit handlers run).
- **Checked.** Crashed 3 of 3 runs before, 0 of 3 after; `tests/test_sound_fx_threads.py`.

## 2026-11-18 19:50 · `91dc4b9` · Authored break blocks are breaks for the timer (issue 6)

- **Why.** `tests/test_timer_break_buffer_behavior.py` failed upstream for the wrong reason (it patched a function the timer no longer uses). Rewritten to test the live path, it exposed a real bug: Kairos v2 dropped `subtype: break` on fixed blocks, so Start day ran a break as work (completion prompt, points).
- **Changed.** The fixed-time block and its timer unit keep the subtype (`_build_conceptual_blocks`, `_build_timer_execution_units`); `runtime._normalize_execution_unit` treats subtype break/buffer as a break.
- **Checked.** `tests/test_kairos_v2_timer_breaks.py`; seven fake-life dumps identical.

## 2026-11-18 19:50 · `b085852` · TRICK manifest, skill template, a JavaScript typo (issues 5, 6)

- **Changed.** `.gitignore`'s `debug_*` hid every new file in `utilities/dashboard/widgets/debug_console/`, so its `trick.yml` never reached the repository; anchored to `/debug_*` and the manifest added. `utilities/registry_builder.py` skips the blank skill skeleton (`docs/agents/skills/template/`). `app.js` `findTrickElement` used Python's `".".join(...)`.
- **Checked.** Full suite 345 passed, **0 failed**: the first fully green suite (upstream has 3 failures).

## 2026-11-18 19:57 · `b99d81a` and 19:59 · `f44f0b4` · Docs aligned with Kairos v2

- **Changed.** The agent scheduling skill rewritten for v2; CLI reference, Kairos elements reference, settings, workflows, dashboard guide, overview and readme corrected (what v2 does not read); out-of-date banners on the two v1 algorithm pages; a dead link removed. New issues logged: 10 (weekly every day, monthly never) and 11 (options v2 never reads).

## 2026-11-18 ~20:30 · no commit · Strategy agreed

- The pilot asked for a strategy before more fixes: "usable by me and some friends first; fix the breakpoints, then build on top; build seamlessly; document everything". `docs/ROADMAP.md` written: the "usable" definition, rules for seamless changes (one shared helper per idea), Kairos v1 vs v2, where inconsistency risk really is (days and periods, free time, item lengths, routines), phases, decisions D1-D4. The tracker became one numbered list (issues 12-19 added). Committed later in `4453c88`.

## 2026-11-18 22:27 · `969cabb` · D1: items without a length get planned (issue 12)

- **Why.** Kairos cannot place a 0-minute item. `new`, Brain Dump and Chore Setup can create items with `duration: 0`. Worse, found while testing: a routine without a length of its own vanished from the plan together with its steps.
- **Decided by the pilot.** A global default length (30); a length field in Brain Dump; a routine is "a placeholder for the things inside it", never left out.
- **Changed.** `kairos_v2._effective_length` (own length or start-end span; routines: total of their steps' known lengths, else the default once; tasks and habits: `default_duration_minutes`), used in `_normalize_candidate` (every candidate) and `_fill_structure_length` (top-level structure, before fixed slots are found). `schedule.assumed_lengths`. Home: **no length** tag and sentences (`home_api.length_notes`), Tasks card wording. Brain Dump: Length field. `user/settings/scheduling_settings.yml`: the setting, and notes on what v2 reads. One builder test changed on purpose (a length-less routine is now one block).
- **Checked.** 20 new tests (17 failed before); suite 365 passed, 0 failed; dumps identical; end to end with the real CLI; headless Chrome (Home tag, Brain Dump field).
- **Details.** `docs/scheduling/item_lengths.md`.

## 2026-11-18 22:27 · `4453c88` · D1 documented; roadmap; D2 proposal

- **Changed.** `docs/ROADMAP.md`, `docs/scheduling/item_lengths.md`, `docs/scheduling/recurrence_design.md` (proposal for issue 10), tracker, handover, item properties, architecture, Home guide, Brain Dump page.
