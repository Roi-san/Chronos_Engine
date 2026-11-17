# Known issues and next steps

One place for what is wrong and what is left to do on branch `home-hub-fixes`.
Add a line when something is found; move it to "Done" (with the commit) when fixed.
Details of how each feature was built live in the design docs linked below; this file only tracks.

Last updated: 2026-11-17.

## Known issues (found, not fixed)

| # | Problem | Where | Found |
|---|---|---|---|
| 1 | **Sleep after midnight empties the day.** A sleep anchor at `00:30` is read as 00:30 *this morning*, so Kairos sees 0 minutes left (`day_budget.remaining_minutes_before_sleep = 0`) and places nothing. Sleep at 23:55 works. Affects anyone who goes to bed after midnight. | `modules/scheduler/kairos_v2.py`, `model_day_budget` / sleep boundary | 2026-11-17, step 3 end-to-end test |
| 2 | **Work is placed after a fixed slot rather than before it.** At 22:05 with Gym fixed at 22:30, a 20-minute task went to 23:15, although 22:07-22:27 was free. Happens with no status involved. | `kairos_v2.py`, gap / remaining-structure placement | 2026-11-17, step 3 end-to-end test |
| 3 | **`python modules/console.py today reschedule` segfaults on exit** (exit 139) when its output is redirected to a file or pipe. The schedule is written before the crash; not seen from the dashboard. Also on the commit before step 3. | console shutdown (likely a native library at exit) | 2026-11-17 |
| 4 | **Completing the same item again on the same day awards points again**; nothing limits it to once a day. Re-check before fixing. | `commands/complete.py` -> `utilities/completion_effects.py` | 2026-11-17, first review |
| 5 | **The registry lists the blank skill template as if it were a real skill.** | `utilities/registry_builder.py`, skills scan (`templates` is not skipped) | 2026-11-17, first review |
| 6 | **Two tests fail on untouched upstream too**: timer break-as-buffer, TRICK debug-console registry. | `tests/test_timer_break_buffer_behavior.py`, `tests/test_trick_debug_console.py` | before this branch |
| 7 | Small, harmless: `/api/profile/avatar` and `generated/settings_bundle.js` return 404 on a fresh install. The "Yesterday Check-in" popup appears even when nothing was scheduled yesterday. | dashboard | `docs/HOME_HUB_HANDOVER.md` |

Older open problems for the friend (task without due date never considered, zero durations, missed morning routine re-queued, routines shown as one block, field names, template choice) are in `docs/HOME_HUB_HANDOVER.md`, "Shaky bits".

## Next tasks

| # | Task | Notes |
|---|---|---|
| 1 | **Commit/push decision**: push `home-hub-fixes` to GitHub so it can be seen and reviewed. | Nothing on this branch is pushed yet. |
| 2 | Fix issue 1 (sleep after midnight). | Suggested next. Needs a test with sleep at 00:30 and 01:00. |
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

## Done on this branch

| Commit | What |
|---|---|
| (this commit) | Status scale-down step 3: Home "Saved for a better day" + Add back, "tough today" kept notes; Add back restores a fixed slot's time |
| `9c7da21` | Status scale-down step 2: fixed template slots |
| `4b2c818` | Status scale-down step 1: flexible items |
| `30ea006` | A weight of 0 switches a scheduling factor off |
| `9c3383f` | Finished one-off tasks no longer come back the next day |
| `e01ac10` | Docs describe what Kairos v2 actually reads and how it plans |
| `e6c65f5` | Habit module fix and stale docs |

## Where the details are

- Status scale-down plan, decisions and step-by-step log: `docs/scheduling/status_scale_down_design.md`
- Goals and commitments in scheduling: `docs/scheduling/direction_goals_commitments.md`
- Everything the `home-hub` branch changed: `docs/HOME_HUB_HANDOVER.md`
- Item fields and what Kairos does with them: `docs/reference/item_properties.md`
