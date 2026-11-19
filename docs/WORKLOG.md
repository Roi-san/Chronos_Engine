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

## 2026-11-18 ~22:45 · `0454ff7` · START_HERE, this work log, regression scripts in the repo

- **Changed.** `docs/START_HERE.md` (orientation for a new session), `docs/WORKLOG.md` (this file), `scripts/regression/` (the fake-life dumps, probes and browser check that only lived in temporary folders), links at the top of `docs/index.md`.

## 2026-11-18 ~22:50 · `65355e2` · Step 1b: habit tests; item modules found next to item_manager

- **Why.** The habit module once went months without loading and nothing noticed; recurring items (D2) will depend on habit completion history.
- **Changed.** `tests/test_habits.py` (15 tests): the habit module loads and is reached by dispatch; new, complete (completion_dates, last_completed, streaks, bad-habit incidents), track, delete; `complete habit` writes today's completion log and Kairos then drops the habit (`already_completed_today`).
- **Found and fixed.** The test fixture points `item_manager.ROOT_DIR` at a temporary folder, and `dispatch_command` looked for `modules/<type>/main.py` under `ROOT_DIR`, so in every test all item commands silently used the generic handlers. The lookup is now relative to `item_manager.py` (same folder in a normal run).
- **Found, logged.** Issue 20 (tests that write items also write the core mirror `chronos_core.db` of the checkout they run in). Issue 21 (`tests/test_timer_anchor_wait.py` fails between 22:30 and midnight: "90 minutes from now" wraps past midnight). Issue 4 confirmed for habits: the module refuses a second completion today, but `complete` still runs the completion effects (points).
- **Checked.** Full suite 378 passed; the 2 failures are issue 21 and fail the same way on the unchanged code.
- **Next.** Step 1c, recurring items (D2), as written in `docs/scheduling/recurrence_design.md`; not started.

## 2026-11-19 ~00:20 · no commit · A new session picks up

- The previous session (2026-11-18) had stopped at its usage limit right after committing step 1b (`7acaa59`); everything was committed and pushed, and step 1c (D2) had not started. The text the pilot pasted as "the last message" was two earlier messages drawn over each other in the terminal; the session transcript showed the real end. All docs, the tracker, the roadmap and the pilot's messages from every session were read again before any work.

## 2026-11-19 ~01:35 · `0d0578a` · Step 1c: recurring items (D2); the Chore Setup wizard works

(This entry replaced an "IN PROGRESS" note written at the start of the step, which only said the step was being built and where its build log was.)

- **Why.** Issue 10: `weekly` was planned every day, and `monthly` / `quarterly` / `yearly` never; the Chore Setup wizard writes exactly these.
- **Decided.** The D2 proposal (pilot, 2026-11-18). Then, before building, a check against the wizard showed that items without a `day:` would all join on the first day of their period (the 6 monthly chores, 3 hours, on the 1st; 14 chores on 1 January): the pilot chose option B, spread them ("most definitely B", 2026-11-19, with "be EXTREMELY CAREFUL ... i dont want that to interfere with other things"). Added while building (design decision 9, reported to the pilot): an item added after its turn this period starts with its next turn, so setting up chores mid-period does not put every passed turn on the plan as "missed".
- **Changed.**
  - `modules/scheduler/periods.py` (new): the one shared helper for days and periods (`today`, `normalize_period`, `period_bounds` and `previous_period_bounds` for day to year, `period_length`, `period_key`, `parse_day`, `completed_names_by_date` with the fast YAML parser, `mini_names_for`, `done_dates`).
  - `modules/scheduler/recurrence.py` (new): the rules (`parse_frequency`, `preferred_day`, `spread_turns`, `evaluate`, `pressure_signal`, `read_library`, `log_window_start`, `evaluate_library`, `load_recurring`; constants `RECURRING_MAX_BONUS = 24`, `MISSED_PUSH = 0.2`).
  - `modules/scheduler/direction.py`: its period and log functions moved to `periods.py` (the old names stay, pointing there); `load_direction` reads the logs once for commitments and recurring items and returns `recurring`; recurring pressure is a third signal; `bonus_for` adds its points. A failure in recurring items cannot cost goals and commitments.
  - `modules/scheduler/kairos_v2.py`: `build_candidate_universe` asks the recurring result whether an item is on today's plan (fallback when it is missing: shown, never hidden); `_frequency_applies_to_date` rewritten as that fallback (daily and weekday items exactly as before); `_recurring_record` writes `schedule.recurring`; `_status_importance` adds recurring pressure (never urgency); `direction.pushed_items` carries the recurring reason; phase notes for the decision log.
  - `modules/commitment/main.py`: periods, keys and "done" from the shared helper; the tracker reads the daily logs (Start-day completions count, issue 24), uses the day it is given, understands quarter and year, reads dates written without quotes; it still counts each completion (issue 28).
  - `modules/item_manager.py`: `generic_handle_new` stamps `created` on new habits, tasks, routines, subroutines, microroutines and timeblocks.
  - `utilities/dashboard/home_api.py`: recurring reasons and state on Home; the kept sentence for recurring importance; `periods.today()`.
  - `utilities/dashboard/wizards/chore_setup/index.js`: built-in chores created from the wizard's own list when no `_example` habit exists (issue 22); custom chores sent in the right shape (issue 29); only meaningful fields; each chore checked after it is made, failures named; day picker for weekly and monthly chores; `created`; the custom row on two lines.
  - `user/settings/scheduling_priorities.yml`: the Recurring Pressure row.
  - Tests (new): `tests/test_periods.py`, `test_recurrence.py`, `test_kairos_v2_recurrence.py`, `test_commitment_periods.py`, `test_home_api_recurrence.py`, `test_item_created.py`. Scripts (new): `scripts/regression/chores_month.py`, `chore_setup_check.js`, `chore_files.py`.
- **Checked.** 106 new tests, written first (98 failed before, 8 controls passed); full suite 486 passed, 0 failed (380 before); four deliberate breaks were each caught by the tests; fake-life dumps identical except `rich_dump`, where the weekly "Read" habit is no longer planned before its Thursday turn; the wizard walked to the end in headless Chrome before (said 7 created, made 1 wrong file) and after (7 correct files); the real `today reschedule` with the wizard's chores; Home's "Right now" in headless Chrome showing a missed weekly chore's reason; four simulated weeks with all 26 wizard chores (at most 2 once-per-period chores on a day; a skipped chore came back daily until done).
- **Found, logged.** Issues 22 to 30 (22, 27 and 29 fixed in this step; 24 fixed for commitments, open for habit streaks; 23, 25, 26, 28 and 30 open).
- **Details.** `docs/scheduling/recurrence_design.md` (decisions 1 to 9, the rule as built, tests, verification, limits, build log).

## 2026-11-19 ~01:50 · `0d0578a`, docs `3e12da5`, `b1f223e` · Step 1c committed; new branch `usable-chronos`

- **Handover restored.** `docs/HOME_HUB_HANDOVER.md` had been overwritten by accident in the pilot's editor (an older copy with a stray `/`); restored from the last commit with `git restore`, then the three step-1c additions put back (recurring items, the Chore Setup fix, the test count).
- **Committed and pushed** on `home-hub-fixes`: code `0d0578a`, docs `3e12da5`, regression README `b1f223e`. Every "not committed yet" placeholder replaced by the hash.
- **New branch `usable-chronos`** from `home-hub-fixes` at `b1f223e`, at the pilot's request. All future work goes there.
- **`docs/NEXT_SESSION.md`** (new): where things stand, the order of work, the biggest obstacles to smooth scheduling, how the pilot wants the work done. START_HERE points to it; the roadmap has the obstacle list.

## 2026-11-19 ~16:25-21:25 · `cfc5d38` · Evaluation as a new user; issue 31 fixed

- **Why.** The pilot asked whether a new user can already benefit from Chronos ("just test, try to break it, don't change code"), then asked why onboarding fails and to fix the crash on one broken file.
- **Evaluation (no code changed).** A fresh throwaway export, the dashboard in headless Chrome and the real commands: splash, onboarding, Life Setup, Home capture, Plan my day, Done / Skip / Re-plan, Start day, the next day, Goal Planning, Sick day; then stress scenarios on a fake user (an overloaded day, overlapping fixed blocks, odd input, night owl, a task longer than any gap, no template, an impossible commitment, a big life of 64 items, a sick day). Works: Life Setup, capture, planning, Right now, Done / Skip / Re-plan, Start day, carry-over, goals pushing their habits, chores, night owl, scale-down, odd names and lengths. Found and logged: issues 31 to 37. The summary and where to draw the line are in `docs/NEXT_SESSION.md`.
- **Issue 31 fixed.** `modules/scheduler/v1.py`: `read_template` catches YAML, decoding and file errors, returns None like a missing file (every caller already treats None as "nothing here") and notes the file in `UNREADABLE_FILES`. `modules/scheduler/kairos_v2.py`: `generate_schedule` clears that list at the start of a run; `_record_unreadable_files` writes `schedule.unreadable_files` ([{file, error}]), a decision-log note and a console line. Not changed: the reading encoding (issue 35).
- **Checked.** `tests/test_unreadable_files.py`, 7 tests written first (all 7 failed before); full suite 493 passed, 0 failed; the five fake-life dumps identical; the real `today reschedule` with a broken habit file plans the day and names the file.
- **Onboarding (issue 32), explained, not changed.** Its examples were dropped from the repository in `alpha_v0.3`; `copy` cannot find them and the dashboard reports success anyway. Needs the pilot's choice of fix.

## 2026-11-19 ~21:30-21:45 · no commit · Routines, day templates, goals and commitments checked

- **Why.** The pilot asked whether routines and templates work at all ("if I set a bedtime routine, will it get scheduled? a Perfect or Sick day template?") and how far goals and commitments are useful.
- **How (no code changed).** A fresh throwaway export (`scratchpad/tr`). Routines and templates: files shaped like the Routine Builder and Day Builder save them, planned by the real Kairos v2 at a fixed clock (`scratchpad/tr.py`, `tr2.py`). Goals and commitments: created through the dashboard server's `/api/item` with Home's exact payloads, the real `today reschedule`, `mark` (Home's Done), `commitments check`, `track goal`, `/api/milestone/update`; plans for Friday to the next Sunday at fixed clocks (`scratchpad/plan_at.py`, `cm_status.py`).
- **Found, logged.** Issues 38 ("bedtime" / "sleep" in a name hides the item), 39 (routines only on a day template), 40 (a day-specific template loses to a general one), 41 (goal and commitment forms; milestone progress and a crash).

## 2026-11-19 ~22:00-22:45 · `feec244`, `19353dc`, `4ee70d3` (conftest) · Onboarding fixed; milestone progress; tests kept out of the pilot's data; planning and tracking model

- **Why.** The pilot: commit the earlier work (done: `cfc5d38` code, `c5a631a` docs, pushed), "make sure the onboarding situation actually works", take on one or two sure fixes, and think through naming ("a wind-down routine or bedtime routine are the same"), template choice ("if I select a Perfect day, Kairos should pick up on that"), "how often / when", goal progress and skips, with Kairos as the backbone and no mismatches anywhere. Ask on architectural decisions.
- **Onboarding (issue 32), option A** (the earlier recommendation; the pilot asked for onboarding to work without choosing, so this is a call that follows from their rules: veto welcome). Dashboard: step 4 "Your Day" opens Life Setup and Chore Setup and shows what exists; step 5 "Goals & Commitments" opens Goal Planning; the last step lists only what was saved and what is on disk. **Removed** from `utilities/dashboard/wizards/onboarding/index.js`: the example-clone UI of steps 4 and 5 (10 examples), `copyItem`, `state.createdItems`, and the step titles "Templates & Routines" and "Goals, Commitments, Rewards". Console: `modules/onboarding_wizard.py` no longer writes an empty day template; the steps without examples point to the real tools; the missing-examples warning is gone. Details in the tracker's Done row.
- **Issue 41 c, d** (milestones): text measures no longer crash the evaluation, one bad milestone no longer stops the rest, completed means 100% (`settle_progress`, also called by `set`).
- **Found and contained: tests wrote into the pilot's item mirror** (`user/data/chronos_core.db`). This session's 9 rows were deleted right away (backup first, in the session scratchpad `db_backup/`; only rows from the temporary test folder with this evening's timestamp); `databases.yml`'s `last_sync` for the core mirror kept the new timestamp (2026-11-19T22:35:17). New `tests/conftest.py` switches the mirror off in tests. 13 older test rows remain for the pilot to decide (#45).
- **Checked.** 10 new tests (7 failed before); full suite in a throwaway copy: 501 passed, 2 failed (issue 21's clock window, 22:37); headless-Chrome onboarding walk before and after, plus a real Life Setup walk started from onboarding; files and the mirror checked on disk. No scheduling code changed, so no fake-life dumps were needed.
- **Design.** `docs/scheduling/planning_and_tracking_model.md`: three rules (meaning from what the user set, never from names; every form writes what Kairos reads; one record of what happened), a map of each concept, proposals A to E and decisions D5 to D11, and an order. New issues 42 (an item's own time is ignored), 43 (the sleep wind-down pack is never planned), 44 (hand-completed milestones give no points or triggers), 45 (old test rows in the mirror).
- **Docs touched.** Tracker (rows 42 to 45, three Done rows, a dated note on #32), this log, `docs/NEXT_SESSION.md`, `docs/ROADMAP.md` (decisions D5 to D11, a log line), `scripts/regression/README.md` (the onboarding walk), `docs/readme.md` (what onboarding does, dated).

## 2026-11-19 ~22:50-23:25 · `4ee70d3` (timer test), `5566407` · Issue 21, mirror clean-up, D5, D6, D7

- **Why.** The pilot: delete the two old failing tests if unhelpful, eject the 13 old test rows (#45), explain how templates work now, keep writing everything down for the next session, "don't stick to my input, discard it if that makes your work easier"; decisions: D5 "go with your gut", D6 yes, D7 a wish and appointments locked in place; "do these things before moving on".
- **Read first** (asked by the pilot): `docs/START_HERE.md` and `docs/ISSUES_AND_NEXT_STEPS.md` in full (since the conversation was compacted only `docs/NEXT_SESSION.md` had been read in full). Found that way: issue 20 already recorded the mirror leak and said to run tests only in an export; this session had run two test files in the repo anyway (now noted in the tracker and the Done row).
- **Issue 21** (`tests/test_timer_anchor_wait.py`): kept, not deleted. The tests check that Start day waits for a fixed block still ahead (useful); only their clock was wrong. Fixed clock at 08:30, one test added for the opposite case. At 23:04: new 4 passed, old 2 failed.
- **#45**: the 13 test rows deleted from `user/data/chronos_core.db` after a backup (`db_backup2/` in the session scratchpad); selected by their paths (`.tmp_test_kairos_v2_user...` and `...AppData/Local/Temp/tmp...`); the 7 relations all belong to the pilot's Life Skeleton and stay.
- **D5, D6, D7**: built as described in the Build log of `docs/scheduling/planning_and_tracking_model.md` and the tracker's Done rows. On the way: #46 (Sleep Settings sleep blocks were not sleep; fixed by D5), #47 (fixed library items are never planned; with appointments, #17), #48 (two small name-based sleep leftovers, left as they are). One of my D7 tests was wrong at first (a wish at 12:00, inside Work); corrected. Another needed the shipped status settings (the test fixture knows only energy and focus without their scales), copied into the fake user read-only.
- **Checked.** 32 new tests (13 + 9 + 10; 31 failed before, 1 guards unchanged behaviour), plus the timer test; full suite in a throwaway export: 517 (after D5), 526 (after D6), **536 passed, 0 failed** (after D7, 23:18); nine fake-life dumps and probes identical before and after; the real `today reschedule` with a copy of the pilot's day template (their Core Sleep is found by its marks; a Bedtime Routine is planned; two wishes for 23:30: one kept, one moved, Home says why); Home in headless Chrome (template line and plan note shown, no page errors).
- **Docs touched.** Tracker (notes on #16, #17, #20, #21, #38, #39, #40, #42, #43, #45; rows #46-#48; four Done rows; header now names `usable-chronos`), the design doc (status, decisions, Build log, log), `docs/ROADMAP.md` (D5-D7 decided, log), `docs/reference/item_properties.md` (sleep, days, template choice, an item's own time, sleep anchors), `docs/scheduling/sleep_after_midnight.md` (sleep anchor definition, dated), `docs/scheduling/builder_templates_prototype.md` (template choice, dated), `docs/agents/skills/scheduling/skill.md`, `docs/HOME_HUB_HANDOVER.md` (shaky bit 7, dated note for the friend), `docs/START_HERE.md` (where things live, the one-page Kairos map, where things stand), `docs/NEXT_SESSION.md`, this log.

## 2026-11-19 ~23:35-23:45 · `feec244`, `19353dc`, `4ee70d3`, `5566407`, docs after them · Committed and pushed

- **Why.** The pilot: "ok commit and push these changes".
- **Commits.** `feec244` onboarding (#32); `19353dc` milestone progress (#41 c, d); `4ee70d3` tests: `tests/conftest.py` (#20) and the timer test clock (#21); `5566407` Kairos D5, D6, D7 with their tests and Home's lines. D5 to D7 are one commit, not three as `docs/NEXT_SESSION.md` planned: they share hunks in `kairos_v2.py` and `home_api.py`, and splitting them would have produced commits whose state was never tested. The full suite on the committed tree alone (a fresh `git archive HEAD`): 536 passed, 0 failed.
- **Tracker.** Every "not committed yet" replaced by its hash. Moved out of the Known table, as the tracker's rule asks (fixed; their description lives in the Done rows and the entries above): #20, #21, #32, #38, #43, #45, #46. Still in the table with dated notes, partly open: #16 (picker later), #39 and #42 (no time or how-often fields in the forms yet), #40 (Day Builder has no Days field).

## 2026-11-19 ~23:40 to 2026-11-20 ~00:10 · `a5c0f63` · D8 parts of the day and the form fields; D9 Skip this week

- **Why.** The pilot: "commit and push these changes" (done, see the entry above), "about D8 the answer is 8, the most intuitive answer" (read as yes; written down so it can be corrected), "D9 also a yes", then commit and push "once tested to be working flawlessly"; "think in the grand scheme ... absolute modularity but also overall perfect cohesion".
- **Built.** As in the Build log of `docs/scheduling/planning_and_tracking_model.md` and the tracker's two Done rows. New modules: `modules/scheduler/day_parts.py`. Changed: `kairos_v2.py`, `recurrence.py`, `periods.py` (shared log loop), `direction.py`, `commands/mark.py`, `home_api.py`, Home, the Routine Builder. New tests: `tests/test_wished_parts.py` (13), `tests/test_skip_turn.py` (13), one more in `tests/test_wished_time.py`. New browser check: `scripts/regression/when_and_skip_check.js`.
- **Mistakes on the way, corrected.** A test read `schedule.recurring.by_identity`, a shape that exists only inside direction; the schedule records `schedule.recurring.items` (Home's helpers were fixed the same way before anything shipped). One assertion I first wrote could never fail (a fallback list); removed. A shell heredoc broke on quotes twice; the edits went through script files instead.
- **Found and logged.** #49 (a part wish cannot land inside a template window), #50 (before bed for a night owl is before 23:59 until issue 9).
- **Checked.** 27 new tests (the 3 guards of unchanged behaviour passed before, every other one failed before); full suite 563 passed, 0 failed (00:06, final tree); nine fake-life dumps and probes identical; the browser walk: run three times on a throwaway copy with the pilot's day template copied in (Core Sleep 02:00-10:30), after midnight on 2026-11-20. Home's capture box wrote `frequency: daily, when: before bed` / `frequency: ""` / `start_time: 19:30`, and the next item no longer inherits When; the Routine Builder saved, reloaded and cleared How often and When on disk; the plan put the Bedtime Routine at 01:05-01:30 and "Read in bed" at 01:30-02:00 (ending at the real 02:00 bedtime); "Skip this week" showed only on the weekly Laundry, wrote `status: skipped, skip: period`, and after a re-plan Laundry was gone and Home said "Skipped this week: Laundry. It is back next week."; no page errors. The walk found three things, fixed before the commit with a test each where Kairos was involved: (1) When and How often carried over to the next capture (Home kept the whole draft except the name; they now reset after Add); (2) a part of the day lying after where tonight's plan ends (a night owl's morning at 00:05) was placed after bedtime (parts are now clipped to the plan's end; `test_a_part_after_bedtime_is_not_in_this_plan`); (3) a clock-time wish after bedtime said "it would run into bedtime" (now "19:30 is after bedtime (02:00), where this plan ends"; `test_a_time_after_bedtime`)
- **A slip in the docs step, corrected.** The first run of the doc script for this entry used a draft that still said "not committed yet", 561 tests and the old test counts (my patch to the draft failed on one string and the next command ran anyway). Corrected in place right after: hashes, 563, the counts above, and the three findings of the browser walk in the design doc's Build log. Checked with a grep for "not committed yet" and "561".
- **Also updated.** `docs/NEXT_SESSION.md` (newest state first; next: D10, D11, then step 3), `docs/START_HERE.md` (`day_parts.py`, where things stand), the scheduling skill, the friend's handover note (shaky bit 7), `scripts/regression/README.md` (the new browser walk). Home's capture box keeps "For goal" and "Lighter version of" after Add as before (unchanged on purpose; only When, At and How often reset).
