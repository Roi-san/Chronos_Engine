# Known issues and next steps

One place for what is wrong and what is left to do on branch `home-hub-fixes`.
Add a line when something is found; move it to "Done" (with the commit) when fixed.
Issue numbers stay the same when an issue is fixed, so references elsewhere keep working.
Details of how each feature was built live in the design docs linked below; this file only tracks.

Last updated: 2026-11-18.

## Known issues (found, not fixed)

| # | Problem | Where | Found |
|---|---|---|---|
| 4 | **Completing the same item again on the same day awards points again**; nothing limits it to once a day. The CLI reference treats `mark` plus `complete` on one block as "two events", so this needs a decision: once per item per day, or allowed for things done several times a day. | `commands/complete.py` -> `utilities/completion_effects.py` | 2026-11-17, first review |
| 7 | Small: `/api/profile/avatar` and `generated/settings_bundle.js` return 404 on a fresh install (harmless). The "Yesterday Check-in" popup shows on startup whenever there is anything you could log, even if nothing was scheduled yesterday. That is the friend's design (it lets you log unscheduled things); it shows once a day until dismissed. Open question for the pilot: show it only when something was scheduled. | dashboard; `popups/yesterday_checkin/index.js` (`hasChoices`) | `docs/HOME_HUB_HANDOVER.md`; popup checked 2026-11-18 |
| 8 | **Several sleep blocks: a nap ends the day.** With a nap and a night sleep (the Sleep wizard's "biphasic" mode: core sleep plus 14:00-15:00), the day ends at the nap, 14:00. Sleep blocks other than the one that ends the day are never kept free of work (polyphasic: only one block counts). The pilot chose not to fix this with issue 1 (2026-11-18); they have one sleep block. | `kairos_v2._resolve_next_bedtime` (soonest bedtime wins); sleep anchors are left out of `commit_anchor_skeleton` | 2026-11-18, issue 1 work |
| 9 | **Nothing is planned between midnight and a bedtime after midnight** until you re-plan after midnight, and then it counts as the new calendar day (daily habits can show up again). By design for now; see "a day that lasts until bedtime" below. | `kairos_v2.PLAN_LAST_MINUTE_OF_DAY`; calendar date everywhere | 2026-11-18, issue 1 decision |
| 10 | **`frequency: weekly` is planned every day, and `monthly` / `quarterly` / `yearly` are never planned.** Kairos only understands `daily` and weekday names. The Chore Setup wizard's built-in chores use exactly these: each of its 7 weekly chores you activate (laundry 60 min, vacuum, mop, bathroom, sheets, trash, plants: about 3 h 10 min together) would be planned every day, and its 14 monthly, quarterly and yearly chores never. Needs a decision on what "weekly" means: a set weekday, or once a week until done. | `kairos_v2._frequency_applies_to_date`; `wizards/chore_setup/index.js` | 2026-11-17 (weekly); 2026-11-18 (monthly, chores) |
| 11 | **Some scheduler options do nothing in Kairos v2.** `buffers:`, `breaks:`, `sprints:`, `ignore-trends`, `quickwins:N` and the status threshold are parsed by `today` and sent by the Today widget's toggles, but never read. The widget's weight sliders (`prioritize:`, `custom_property:`) only steer which day template is chosen. Now documented (CLI reference, dashboard guide, scheduling skill), but the controls still look like they work. | `commands/today.py` (parsed into the run context), `modules/scheduler/kairos_v2.py` (not read); `widgets/today/` | 2026-11-18 |

Older open problems for the friend (task without due date never considered, zero durations, missed morning routine re-queued, routines shown as one block, field names, template choice) are in `docs/HOME_HUB_HANDOVER.md`, "Shaky bits".

## Next tasks

| # | Task | Notes |
|---|---|---|
| 1 | Keep `origin/home-hub-fixes` up to date: push after each commit. | Pushed after every commit so far (2026-11-18). |
| 2 | Decide how light days should be laid out (pack from now, or spread out). | Open decision with the options: `docs/scheduling/gaps_and_breathing_room.md`, "Open decision: light days". |
| 3 | No automated test for habits (`modules/habit/main.py` was broken on upstream for a long time without any test noticing). | Write tests for new / track / complete / delete. |
| 4 | Stale scheduling docs still describe the archived v1 scheduler (`kairos.py`, `weekly_generator.py`). | Partly done 2026-11-18: out-of-date banners on `scheduling_algorithm_overview.md` and `scheduling_algorithm_deep_dive.md`; corrected the scheduling skill, `cli_commands.md` (`today`), `kairos_elements_reference.md`, `guides/settings.md`, `guides/common_workflows.md`, `guides/dashboard.md`, `documentation_overview.md` and `readme.md`. Left: rewrite the two v1 pages for v2, or retire them in favour of `docs/dev/architecture.md`. |
| 5 | Release notes for this branch's changes. | `docs/changelog.md` |
| 6 | Feature docs that are missing or thin. | from the first review |

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

- Status scale-down plan, decisions and step-by-step log: `docs/scheduling/status_scale_down_design.md`
- Where the day ends (bedtimes after midnight, no sleep block, the sleep prompt): `docs/scheduling/sleep_after_midnight.md`
- Gaps, urgent work and breathing room, plus the open "light days" decision: `docs/scheduling/gaps_and_breathing_room.md`
- Goals and commitments in scheduling: `docs/scheduling/direction_goals_commitments.md`
- Everything the `home-hub` branch changed: `docs/HOME_HUB_HANDOVER.md`
- Item fields and what Kairos does with them: `docs/reference/item_properties.md`
