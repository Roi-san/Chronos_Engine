# Known issues and next steps

One place for what is wrong and what is left to do on branch `home-hub-fixes`.
Add a line when something is found; move it to "Done" (with the commit) when fixed.
Issue numbers stay the same when an issue is fixed, so references elsewhere keep working.
Details of how each feature was built live in the design docs linked below; this file only tracks.
The order of work, and why, is in `docs/ROADMAP.md`.

Last updated: 2026-11-19.

## Known issues (found, not fixed)

| # | Problem | Where | Found |
|---|---|---|---|
| 4 | **Completing the same item again on the same day awards points again**; nothing limits it to once a day. The CLI reference treats `mark` plus `complete` on one block as "two events", so this needs a decision: once per item per day, or allowed for things done several times a day. Confirmed for habits (2026-11-18): the habit module refuses a second completion today, but `complete` still runs the completion effects (points). | `commands/complete.py` -> `utilities/completion_effects.py` | 2026-11-17, first review |
| 7 | Small: `/api/profile/avatar` and `generated/settings_bundle.js` return 404 on a fresh install (harmless). The "Yesterday Check-in" popup shows on startup whenever there is anything you could log, even if nothing was scheduled yesterday. That is the friend's design (it lets you log unscheduled things); it shows once a day until dismissed. Open question for the pilot: show it only when something was scheduled. | dashboard; `popups/yesterday_checkin/index.js` (`hasChoices`) | `docs/HOME_HUB_HANDOVER.md`; popup checked 2026-11-18 |
| 8 | **Several sleep blocks: a nap ends the day.** With a nap and a night sleep (the Sleep wizard's "biphasic" mode: core sleep plus 14:00-15:00), the day ends at the nap, 14:00. Sleep blocks other than the one that ends the day are never kept free of work (polyphasic: only one block counts). The pilot chose not to fix this with issue 1 (2026-11-18); they have one sleep block. | `kairos_v2._resolve_next_bedtime` (soonest bedtime wins); sleep anchors are left out of `commit_anchor_skeleton` | 2026-11-18, issue 1 work |
| 9 | **Nothing is planned between midnight and a bedtime after midnight** until you re-plan after midnight, and then it counts as the new calendar day (daily habits can show up again). By design for now; see "a day that lasts until bedtime" below. | `kairos_v2.PLAN_LAST_MINUTE_OF_DAY`; calendar date everywhere | 2026-11-18, issue 1 decision |
| 11 | **Some scheduler options do nothing in Kairos v2.** `buffers:`, `breaks:`, `sprints:`, `ignore-trends`, `quickwins:N` and the status threshold are parsed by `today` and sent by the Today widget's toggles, but never read. The widget's weight sliders (`prioritize:`, `custom_property:`) only steer which day template is chosen. Now documented (CLI reference, dashboard guide, scheduling skill), but the controls still look like they work. | `commands/today.py` (parsed into the run context), `modules/scheduler/kairos_v2.py` (not read); `widgets/today/` | 2026-11-18 |
| 13 | **Tasks with no due date are never considered**, even when a window's tag filter matches them: a library task needs a frequency, a due date, a deadline, or a goal or commitment push. `task_defaults.yml` gives tasks made with `new` a due date of tomorrow, which hides this for them. | `kairos_v2.build_candidate_universe` | handover shaky bit 2 |
| 14 | **A missed fixed-time item comes back later in the day**: a routine whose slot has passed is re-queued into the next gap as one unit (a morning routine at 15:30). Needs a rule. | `kairos_v2.py`; `docs/scheduling/builder_templates_prototype.md`, "Missed timed routines" | handover shaky bit 4 |
| 15 | **Routines show as one block**: Home and the timer say "Morning Routine", not the current step. | conceptual blocks, timer units, Home | handover shaky bit 5 |
| 16 | **Day template choice**: with several eligible templates and no status requirements, the alphabetically first wins. | `kairos_v2` template selection | handover shaky bit 7 |
| 17 | **Appointments, reminders and alarms do not block time.** An appointment has to be added to the day template as an anchored timeblock. | `kairos_v2.commit_anchor_skeleton` (reads only the template and hard injections) | handover, "What Kairos actually takes into account" |
| 18 | **No breaks inside long blocks in Start day.** The timer runs each planned block as one stretch; timer profiles' focus/break lengths are only used when the timer is started by hand. v1 put breaks into the plan; v2 leaves this to the timer by design (`timer_owns_execution_shaping`), which does not do it yet. | `modules/timer/main.py` (`start_schedule_plan`) | 2026-11-18 |
| 19 | **Kairos v1 leftovers.** Nothing runs v1, but these remain: stubs `kairos.py`, `weekly_generator.py`, `verify_kairos.py`; `tests/test_kairos.py` (cannot pass, left out of the suite); `user/settings/scheduling_priorities_legacy.yml`; `user/settings/scheduling_defaults.yml` (pre-Kairos settings, not read by v2; `scheduling_settings.yml` now says which of its keys v2 reads); the unreachable pre-Kairos scheduler in `commands/today.py`; the options in #11. Clean-up is the friend's call. The full v1 stays readable in git history (`b1b0bb2`), so removing the stubs loses nothing. | `docs/ROADMAP.md`, "Kairos v1 and v2" | 2026-11-18 |
| 20 | **Tests that write items also write the core mirror** (`user/data/chronos_core.db`) of the checkout they run in: `item_manager.write_item_data` calls `sequence.core_builder.upsert_item_in_core_db`, whose paths are fixed at import, so the fixture cannot redirect them. Run the suite only in a throwaway export (START_HERE). | `modules/sequence/core_builder.py`, `modules/sequence/registry.py` | 2026-11-18, step 1b |
| 21 | **`tests/test_timer_anchor_wait.py` fails between 22:30 and midnight**: it builds "90 minutes from now" as a clock time, which wraps past midnight. A test bug, not a timer bug; the fix is a fixed clock in the test. | `tests/test_timer_anchor_wait.py` | 2026-11-18, step 1b |
| 23 | **The dashboard counts a console command as done whenever it exits normally**, even when it printed an error (`run_console_command`: `ok = returncode == 0`, and commands such as `copy` print "does not exist" and return normally). Every wizard or widget that trusts that answer can report success for a failure; this is how the Chore Setup wizard said "Created 7 chores" while creating none (issue 22). The wizard now checks each chore itself; the cause is not fixed. Fix later: commands exit non-zero on failure, or the server reads a result line. | `utilities/dashboard/server.py` (`run_console_command`), `commands/*.py` | 2026-11-19, step 1c |
| 24 | **Start day records a completion only in the day's log**, never in the item's `completion_dates` (`modules/timer/main.py`, `_record_schedule_completion`). The scheduler always read the logs; the commitment tracker did not, so a habit done through Start day did not count toward its commitment in the Commitments widget or for its triggers (**fixed in step 1c**: the tracker reads the logs now). Still open: habit streaks (`current_streak`, `longest_streak`) and `completion_dates` miss Start-day completions. Fix later: one "record a completion" function used by Home's Done, `complete`, `did` and the timer. | `modules/timer/main.py`, `modules/habit/main.py` | 2026-11-19, step 1c |
| 25 | **A third copy of the period code** in `commands/review.py` (`_period_bounds`, for daily, weekly and monthly reviews), separate from the shared helper `modules/scheduler/periods.py`. It agrees with it today (ISO weeks, calendar months); it should move onto the helper so it cannot drift. | `commands/review.py` | 2026-11-19, step 1c |
| 26 | **Frequencies Kairos does not understand are never planned, silently for the pilot**: `biweekly`, `every 2 days`, `weekdays`, three-letter weekday names in `frequency` (`mon`). Since step 1c they are listed in the schedule file (`schedule.recurring.unrecognised`) and the decision log, but Home does not show them. Fix later: a Home note, or understanding more values (needs a decision on which). | `modules/scheduler/recurrence.py` (`parse_frequency`), Home | 2026-11-19, step 1c |
| 28 | **Commitments are counted two ways.** The tracker (`modules/commitment/main.py`: the Commitments widget, `commitments check`, triggers) counts each completion, so two on one day count twice, which per-target counts ("post 10 times a week") rely on; the scheduler (`direction.py`) counts days. For a period name that is not day/week/month/quarter/year, the tracker counts all-time and the scheduler a week. Older than step 1c, which unified only where periods start and end and which days count as done. Needs a decision: completions or days. | `modules/commitment/main.py`, `modules/scheduler/direction.py` | 2026-11-19, step 1c |
| 30 | **Habit streaks count days, also for weekly or monthly habits**: a weekly habit done every week has a streak of 1. They should count periods (the D2 design's follow-up, `docs/scheduling/recurrence_design.md`, "How it fits the rest"). | `modules/habit/main.py` | 2026-11-18 (design), logged 2026-11-19 |

The field-name decision (`ideal_*` or `start_time`) stays with the friend: `docs/HOME_HUB_HANDOVER.md`, "Shaky bits" 6. The other shaky bits are issues 12 to 17 (12 is fixed, see Done).

## Next tasks

| # | Task | Notes |
|---|---|---|
| 1 | Keep `origin/home-hub-fixes` up to date: push after each commit. | Pushed after every commit so far (2026-11-18). Step 1c (D2) committed as `0d0578a` and pushed (2026-11-19). |
| 2 | Decide how light days should be laid out (pack from now, or spread out). | Open decision with the options: `docs/scheduling/gaps_and_breathing_room.md`, "Open decision: light days". Now part of one free-time policy with #13: `docs/ROADMAP.md`, decision D3 (phase 3). |
| 3 | No automated test for habits (`modules/habit/main.py` was broken on upstream for a long time without any test noticing). | Done 2026-11-18 in `65355e2` (`tests/test_habits.py`). |
| 4 | Stale scheduling docs still describe the archived v1 scheduler (`kairos.py`, `weekly_generator.py`). | Partly done 2026-11-18: out-of-date banners on `scheduling_algorithm_overview.md` and `scheduling_algorithm_deep_dive.md`; corrected the scheduling skill, `cli_commands.md` (`today`), `kairos_elements_reference.md`, `guides/settings.md`, `guides/common_workflows.md`, `guides/dashboard.md`, `documentation_overview.md` and `readme.md`. Left: rewrite the two v1 pages for v2, or retire them in favour of `docs/dev/architecture.md`. |
| 5 | Release notes for this branch's changes. | `docs/changelog.md` |
| 6 | Feature docs that are missing or thin. | from the first review |
| 7 | Fresh-install walkthrough as a new friend: onboarding to the next day's check-in, in a throwaway copy with a headless browser; log every problem here. | `docs/ROADMAP.md`, phase 2 |

### Ideas raised by the pilot, not built

From `docs/scheduling/status_scale_down_design.md`, "Future ideas":

- **Fill freed time with what suits the day**: prefer work that fits today's mood and energy, or goals and commitments falling behind. Today fit only ever subtracts.
- **Move a fixed slot to a later free time** instead of shrinking it.
- **Numeric status weights** (now: order of rows in `status_settings.yml`).
- **A penalty or trigger when a commitment period ends unmet** (`docs/scheduling/direction_goals_commitments.md`).
- **Appointments block time** in the plan (now they must be added as anchored timeblocks).

From `docs/scheduling/sleep_after_midnight.md`, "Future":

- **A day that lasts until bedtime**: for a night owl, plan through midnight to bedtime and keep counting it as "today" (Home, completions, streaks, commitments) until bedtime or wake-up. The pilot's view: the day starts when you wake up and open Chronos. Estimate: several steps, about the size of status scale-down (about 69 calendar-date call sites in Python plus the dashboard). Written down for later at the pilot's request (2026-11-18).

## Done on this branch

| Commit | What |
|---|---|
| `0d0578a` | Issue 10 (roadmap step 1c, decision D2 with option B): `weekly`, `monthly`, `quarterly` and `yearly` work. Each such item is on the plan from its turn (a `day:` you pick for weekly and monthly items, else a day Chronos spreads it to, evenly over the period) until it is done, then gone until the next period; a missed turn comes back daily with a push that grows as the period runs out (new weight row Recurring Pressure; importance on tough days, never urgency). Daily items get a small push after a missed day; weekday items are unchanged. One shared helper for days and periods (`modules/scheduler/periods.py`), used by commitments too: the commitment tracker now counts Start-day completions (issue 24, its commitment part), uses the day it is given, and understands quarter and year. New items record `created`, so chores set up mid-period are not "missed" (design decision 9). Found and fixed on the way: **issue 22**, the Chore Setup wizard said "Created N chores" but created none of its built-in chores (`alpha_v0.3` ships no `_example` habits); **issue 29**, its custom chores were saved as daily habits with no length and a junk `data` field (wrong request shape); **issue 27**, completion logs parsed slowly (62 days: 0.2-0.27 s per plan and per Home load, now 28 ms). The wizard has a day picker. 106 new tests (98 failed before); full suite 486 passed, 0 failed. `docs/scheduling/recurrence_design.md` |
| `65355e2` | Next task 3 (roadmap 1b): `tests/test_habits.py`, 15 tests. Fixed on the way: in tests every item command fell back to the generic handlers (dispatch looked for modules under the fixture's temporary ROOT_DIR). |
| `969cabb` | Issue 12 (decision D1): items without a length are planned. A task or habit without one gets `default_duration_minutes` (30, in `scheduling_settings.yml`); a routine without its own length is one block for the total of its steps (it used to vanish from the plan together with its steps). Home tags such blocks **no length** and says why; Brain Dump has a Length field. Full suite 365 passed, 0 failed. `docs/scheduling/item_lengths.md` |
| `b085852` | Issues 5 and 6: `skills list` no longer shows the blank skill template; the Debug Console's TRICK manifest is committed (`.gitignore`'s `debug_*` silently ignored new files in `widgets/debug_console/`, so it never reached the repository; now anchored to the root); the TRICK highlight lookup no longer throws (`".".join` in `app.js`). With `91dc4b9` the full suite passes for the first time: 345 passed, 0 failed. |
| `91dc4b9` | Issue 6, and the bug it was hiding: a day-template block with `subtype: break` is run by the timer (`start day`) as a break, not as work to complete (Kairos v2 dropped the subtype). The stale timer test now tests the live path. No plan changes: seven fake-life regression dumps are identical. |
| `03b980e` | Issue 3: `today reschedule` from the command line no longer crashes at exit (139). Cause: the "done" chime played on a daemon thread that was still inside pygame when Python shut down. Crashed 3 of 3 runs before, 0 of 3 after. |
| `7c35976` | Issue 2: urgent work takes the earliest gap it fits (it used to jump over gaps under 30 minutes to a later one), and breathing room: the 5 minutes of `buffer_settings.yml` between items and around fixed blocks, only where the day has room, never changing what is planned. `docs/scheduling/gaps_and_breathing_room.md` |
| `d652300` | Issue 1: a bedtime after midnight no longer empties the day (the plan runs to 23:59, or to the bedtime when it is past midnight and still ahead). Also: no sleep block plans until 23:59 instead of 16:00; "go back to sleep" / "shift today later" plan from wake-up instead of planning no flexible work. `docs/scheduling/sleep_after_midnight.md` |
| `04bc2f0` | Status scale-down step 3: Home "Saved for a better day" + Add back, "tough today" kept notes; Add back restores a fixed slot's time |
| `9c7da21` | Status scale-down step 2: fixed template slots |
| `4b2c818` | Status scale-down step 1: flexible items |
| `30ea006` | A weight of 0 switches a scheduling factor off |
| `9c3383f` | Finished one-off tasks no longer come back the next day |
| `e01ac10` | Docs describe what Kairos v2 actually reads and how it plans |
| `e6c65f5` | Habit module fix and stale docs |

## Where the details are

- Order of work, the reasons, v1 vs v2, and the open decisions: `docs/ROADMAP.md`
- Items without a length (D1, issue 12): `docs/scheduling/item_lengths.md`
- Recurring items, weekly to yearly (D2, issue 10; built 2026-11-19), the shared day/period helper, and issues 22-30 found on the way: `docs/scheduling/recurrence_design.md`
- Status scale-down plan, decisions and step-by-step log: `docs/scheduling/status_scale_down_design.md`
- Where the day ends (bedtimes after midnight, no sleep block, the sleep prompt): `docs/scheduling/sleep_after_midnight.md`
- Gaps, urgent work and breathing room, plus the open "light days" decision: `docs/scheduling/gaps_and_breathing_room.md`
- Goals and commitments in scheduling: `docs/scheduling/direction_goals_commitments.md`
- Everything the `home-hub` branch changed: `docs/HOME_HUB_HANDOVER.md`
- Item fields and what Kairos does with them: `docs/reference/item_properties.md`
