# Known issues and next steps

One place for what is wrong and what is left to do on branch `home-hub-fixes`.
Add a line when something is found; move it to "Done" (with the commit) when fixed.
Issue numbers stay the same when an issue is fixed, so references elsewhere keep working.
Details of how each feature was built live in the design docs linked below; this file only tracks.

Last updated: 2026-11-18.

## Known issues (found, not fixed)

| # | Problem | Where | Found |
|---|---|---|---|
| 3 | **`python modules/console.py today reschedule` segfaults on exit** (exit 139) when its output is redirected to a file or pipe. The schedule is written before the crash; not seen from the dashboard. Also on the commit before step 3, and again on 2026-11-18 on untouched `04bc2f0`. | console shutdown (likely a native library at exit) | 2026-11-17 |
| 4 | **Completing the same item again on the same day awards points again**; nothing limits it to once a day. Re-check before fixing. | `commands/complete.py` -> `utilities/completion_effects.py` | 2026-11-17, first review |
| 5 | **The registry lists the blank skill template as if it were a real skill.** | `utilities/registry_builder.py`, skills scan (`templates` is not skipped) | 2026-11-17, first review |
| 6 | **Two tests fail on untouched upstream too**: timer break-as-buffer, TRICK debug-console registry. | `tests/test_timer_break_buffer_behavior.py`, `tests/test_trick_debug_console.py` | before this branch |
| 7 | Small, harmless: `/api/profile/avatar` and `generated/settings_bundle.js` return 404 on a fresh install. The "Yesterday Check-in" popup appears even when nothing was scheduled yesterday. | dashboard | `docs/HOME_HUB_HANDOVER.md` |
| 8 | **Several sleep blocks: a nap ends the day.** With a nap and a night sleep (the Sleep wizard's "biphasic" mode: core sleep plus 14:00-15:00), the day ends at the nap, 14:00. Sleep blocks other than the one that ends the day are never kept free of work (polyphasic: only one block counts). The pilot chose not to fix this with issue 1 (2026-11-18); they have one sleep block. | `kairos_v2._resolve_next_bedtime` (soonest bedtime wins); sleep anchors are left out of `commit_anchor_skeleton` | 2026-11-18, issue 1 work |
| 9 | **Nothing is planned between midnight and a bedtime after midnight** until you re-plan after midnight, and then it counts as the new calendar day (daily habits can show up again). By design for now; see "a day that lasts until bedtime" below. | `kairos_v2.PLAN_LAST_MINUTE_OF_DAY`; calendar date everywhere | 2026-11-18, issue 1 decision |

Older open problems for the friend (task without due date never considered, zero durations, missed morning routine re-queued, routines shown as one block, field names, template choice) are in `docs/HOME_HUB_HANDOVER.md`, "Shaky bits".

## Next tasks

| # | Task | Notes |
|---|---|---|
| 1 | Keep `origin/home-hub-fixes` up to date: push after each commit. | Pushed through the issue 1 fix on 2026-11-18. |
| 2 | Decide how light days should be laid out (pack from now, or spread out). | Open decision with the options: `docs/scheduling/gaps_and_breathing_room.md`, "Open decision: light days". |
| 3 | No automated test for habits (`modules/habit/main.py` was broken on upstream for a long time without any test noticing). | Write tests for new / track / complete / delete. |
| 4 | Stale scheduling docs still describe the archived v1 scheduler (`kairos.py`, `weekly_generator.py`), including `today kairos week`. | `docs/scheduling/scheduling_algorithm_overview.md`, `scheduling_algorithm_deep_dive.md`, `docs/agents/skills/scheduling/skill.md`, `docs/changelog.md` |
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
| (this commit) | Issue 2: urgent work takes the earliest gap it fits (it used to jump over gaps under 30 minutes to a later one), and breathing room: the 5 minutes of `buffer_settings.yml` between items and around fixed blocks, only where the day has room, never changing what is planned. `docs/scheduling/gaps_and_breathing_room.md` |
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
