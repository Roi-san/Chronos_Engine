# Where the day ends: bedtimes after midnight

Status (branch `home-hub-fixes`, 2026-11-18): **implemented**. Fixes issue 1 in `docs/ISSUES_AND_NEXT_STEPS.md`, plus two bugs in the same place that the pilot chose to include. Code: `modules/scheduler/kairos_v2.py` (`model_day_budget`, `_resolve_next_bedtime`, `_derive_emergent_gaps`). Tests: `tests/test_kairos_v2_sleep_after_midnight.py`.

## The problem

Kairos plans flexible work into the time between "now" and the **sleep boundary**: the start of the day template's sleep anchor (`reschedule: never` plus `sleep: true`, category `sleep`, a `sleep` tag, or "sleep"/"bedtime" in the name; **changed 2026-11-19, decision D5:** a block marked as sleep, with or without `reschedule: never`, and a name only on a day with no marked block, see `modules/scheduler/sleep_blocks.py`). The boundary was read as a clock time *on the plan's own date*. So a sleep anchor at `02:00` meant 02:00 **this morning**, and from 02:00 on, Kairos saw 0 minutes left and placed no flexible work.

This hit the pilot every day: their real `user/days/life_skeleton.yml` has **Core Sleep 02:00-10:30** (checked read-only on 2026-11-18). Every re-plan between 02:00 and midnight came back with their fixed blocks (breakfast, work, dinner) and nothing else.

Two more bugs in the same function also emptied the day:

- **No sleep anchor:** the boundary fell back to `24h - target sleep`, which is 16:00 with the default 8 hours. Any plan after 16:00 was empty, and a new user's first day (no day template yet) never got an evening. The pilot's real plan on 2026-11-16 at 22:16 had 0 minutes for this reason.
- **"Go back to sleep" / "Shift today later" planned nothing flexible.** These answers to the sleep prompt (`modules/scheduler/sleep_gate.py`) move the day's start to the end of the sleep block, and the budget and the final block list respected that. Gap finding (`_derive_emergent_gaps`) still started at the clock time, though, so work was placed inside the sleep block and then dropped because it ended before the wake-up time. The result was fixed blocks only, for everyone, not just late sleepers.

### Measured before the fix

Each case was run through Kairos v2 (scratchpad probe `sleep_probe.py`) with the pilot's template shape (sleep, Breakfast 11:00, Work 12:00-15:00, Dinner 21:00-21:30) and 90 minutes of flexible work. The re-plan was `start_from_now`, as Home's Re-plan does.

| Case | Day ended | Flexible items placed |
| --- | --- | --- |
| A. Sleep 02:00-10:30, re-plan at 11:00 | 02:00 | 0 |
| B. Sleep 02:00-10:30, at 22:00 | 02:00 | 0 |
| C. Sleep 02:00-10:30, at 00:30 (after midnight, before bed) | 02:00 | 4 (worked) |
| D. Sleep 02:00-10:30, at 03:00, "stay awake" | 02:00 | 0 |
| E. Sleep 02:00-10:30, at 03:00, "go back to sleep" | 02:00 | 0 |
| F. Sleep 00:30 + 450 min (found 2026-11-17), at 22:04 | 00:30 | 0 |
| G. Sleep 00:00-08:00, at 20:00 | 00:00 | 0 |
| H. Sleep 23:30-07:30, at 22:00 (control) | 23:30 | 4 |
| I. Sleep 23:30-07:30, at 11:00 (control) | 23:30 | 4 |
| J. No sleep anchor, at 22:00 | 16:00 | 0 |
| K. No sleep anchor, at 11:00 | 16:00 | 4 (nothing could go after 16:00) |
| L. Nap 14:00-15:00 + sleep 23:00-07:00, at 11:00 | 14:00 | 4 (nothing could go after 14:00) |

A 23:30 sleeper with "go back to sleep" at 03:00 also got 0 flexible items.

### Why "just make it 02:00 tomorrow" was not enough

Forcing the boundary to 02:00 tomorrow (minute 1560), or even to exactly midnight (1440), still gave an empty evening. Gap records carry both minutes and `HH:MM` text, and the placement code (`_fill_surfaces_with_sequence`) re-reads the text. 1440 and 1560 are written as `00:00` and `02:00`, which read back as this morning, and the gap is thrown away. A boundary of 23:59 (1439) worked. The schedule-file converter (`modules/scheduler/runtime.py`), Home's "Right now" and the Today widget all read `00:00` as minute 0 as well.

## Decisions (pilot, 2026-11-18)

| # | Question | Decision |
| --- | --- | --- |
| 1 | What happens to the time between midnight and a bedtime after midnight (00:00-02:00 for the pilot)? | **Plan up to midnight** for now. After midnight, a re-plan covers midnight to bedtime as the new calendar day, which is how all of Chronos already counts days. Pilot: "the day starts when u wake up ... and you turn on Chronos. thats when the day gets scheduled ... most of the time past midnight you arent onto changing your life and needing pinpoint scheduling." |
| 2 | Make a day last until bedtime (plan through midnight, keep "today" until you sleep)? | Not now. The pilot asked for an estimate first; it is several steps of work (see Future), so it is written down for later. |
| 3 | No sleep anchor? | Plan until the end of the calendar day instead of 16:00. |
| 4 | Several sleep blocks (a nap ends the day at 14:00)? | **Not in this change.** Tracked as a known issue. |
| 5 | "Go back to sleep" / "Shift today later" plan nothing flexible? | Fix it here (one line). |

Implementation choice, not asked: the plan's last minute is **23:59**, not 24:00. Everything that reads a plan takes `00:00` as the start of a day, so ending at 24:00 would need changes in the placement code, `runtime.py`, Home and the Today widget. That work belongs to the "day lasts until bedtime" project, which has to teach all of them about times past midnight anyway. The cost: an item cannot end in the last minute of the day (a 60-minute item does not fit 23:00-24:00).

## The rule

`model_day_budget` asks `_resolve_next_bedtime` for the bedtime that ends this plan. For each sleep anchor with a start time:

- **Starts at 12:00 or later:** a bedtime today (unchanged from before).
- **Starts between 00:00 and 11:59** (`SLEEP_AFTER_MIDNIGHT_BEFORE_MINUTE`): a bedtime after midnight. It is **today** only while the day has not reached it yet and the plan is for today: it is past midnight and you have not gone to bed. Otherwise it is **tomorrow**, at start + 24h.
- The **soonest** of these wins. With only evening sleep anchors, that is the earliest start, exactly what Kairos picked before. The Sleep wizard's weekend output (Core Sleep 23:30 plus "Sleep In" 00:30) ends the evening at 23:30, and at 00:10 at 00:30.

Then the plan stops (`sleep_boundary_minutes`):

| Next bedtime | Plan stops at | `sleep_boundary_source` |
| --- | --- | --- |
| today | the bedtime | `sleep_anchor` |
| tomorrow (after midnight) | 23:59 (`PLAN_LAST_MINUTE_OF_DAY`) | `sleep_anchor_after_midnight` |
| none (no sleep anchor with a start) | 23:59 | `no_sleep_anchor` (was `target_sleep_minutes_fallback`) |

"The day so far" (the floor) is the clock time, or the end of the sleep block after "go back to sleep" / "Shift today later". Gap finding now uses that same floor.

Worked examples (pilot's sleep 02:00-10:30):

| When | Plan covers |
| --- | --- |
| 11:00 or 22:00 | now to 23:59; bedtime recorded as 02:00 tomorrow |
| 00:30 | 00:30 to 02:00 (unchanged) |
| 03:00, "stay awake" | 03:00 to 23:59 |
| 03:00, "go back to sleep" | 10:30 to 23:59 |
| 03:00, no answer given (only `today kairos`, which has no prompt) | 03:00 to 23:59, the same as a 23:30 sleeper at 03:00 already got |

## What changed

All in `modules/scheduler/kairos_v2.py`:

| Where | Change |
| --- | --- |
| module constants | `SLEEP_AFTER_MIDNIGHT_BEFORE_MINUTE = 720`, `PLAN_LAST_MINUTE_OF_DAY = 1439`, with the reasons. |
| `model_day_budget` | Uses `_resolve_next_bedtime`; the plan stops per the table above. `day_budget` gains `bedtime_minutes` (from the start of the plan's date, past 1440 when tomorrow), `bedtime_time`, `bedtime_day` (`today` / `tomorrow`) and `bedtime_anchor`; all are `None` with no sleep anchor. Phase notes gain `sleep_boundary_source`, `bedtime_time`, `bedtime_day`. No longer uses the target sleep length (still used for sleep debt). |
| `_find_sleep_anchors` | New: every sleep anchor of the template, by clock start. `_find_primary_sleep_anchor` now returns its first entry (same result as before). |
| `_resolve_next_bedtime` | New: the rule above. |
| `_derive_emergent_gaps` | Floor = later of the clock time and the sleep-prompt floor (`_sleep_policy_floor_minutes`), the same as `model_day_budget`. |
| `_build_live_commit_summary` | The "Kairos Thinking" line for the budget shows the boundary, its source and the bedtime. |
| `model_reality` | The descriptive `time_budget_rule` label now says `from_now_until_next_bedtime_or_end_of_calendar_day`. Nothing reads it. |

Unchanged on purpose: which nodes count as sleep anchors; sleep anchors still never enter the anchor skeleton (so naps are not kept free); the sleep gate; anything with an evening bedtime.

## Tests

`tests/test_kairos_v2_sleep_after_midnight.py`, 27 tests, written before the code: **24 failed, 3 passed** (controls for behaviour that must not change). After the code: 27 passed.

| Class | What it pins |
| --- | --- |
| `BedtimeAfterMidnight` (9) | The pilot's shape: daytime and evening re-plans get flexible work; nothing ends after 23:59; budget fields; 00:30 runs to 02:00; "stay awake" and "go back to sleep" at 03:00; full-day run without `start_from_now`; decision-log notes. |
| `OtherBedtimesAfterMidnight` (4) | 00:30 with only a duration (the 2026-11-17 case), exactly 00:00, a start with no end or duration, a 05:00 sleeper still up at 03:00. |
| `SeveralSleepBlocks` (2) | Core Sleep 23:30 + Sleep In 00:30: 23:30 wins in the evening, 00:30 wins at 00:10. |
| `EveningBedtimeUnchanged` (4) | 23:30 bedtime: same end, nothing after it; a 13:00 sleep is still today; inside a 23:30 sleep with no answer, nothing new is planned. |
| `SleepPromptAnswers` (3) | "Go back to sleep" and "Shift today later" plan from 07:30 for a 23:30 sleeper; "stay awake" still plans from now. |
| `NoSleepBlock` (3) | Evening gets work; the last gap ends at 23:59, not 16:00; no day template at all. |
| `TheScheduleFileHomeReads` (2) | The evening plan reaches the runtime payload with sane times; the real `today reschedule` command writes it to the schedule file. |

## Verification

- **Full suite** (fresh export, excluding `tests/test_kairos.py` as usual): **314 passed, 2 failed**. Before: 287 passed, the same 2 failures (timer break-as-buffer, TRICK debug-console registry), which also fail on untouched upstream. 314 = 287 + the 27 new tests; no existing test changed result, including the ones whose fixture day has no sleep anchor (it now ends at 23:59 instead of 16:00).
- **Regression dumps, byte-for-byte identical before and after** (scratchpad scripts from status scale-down, all with a 23:00 bedtime): `rich_dump` (7-day rich fake life), `status_week`, `status_matrix`, `fixed_week`, `plan_dump` (base fixture day, no sleep anchor, morning plans).
- **Scenario probe**, same cases as the table above:

| Case | Day ended | Flexible items |
| --- | --- | --- |
| A. 02:00 sleep, 11:00 | 02:00 -> 23:59 | 0 -> 4 |
| B. 02:00 sleep, 22:00 | 02:00 -> 23:59 | 0 -> 4 (22:00-23:30) |
| C. 02:00 sleep, 00:30 | 02:00 -> 02:00 | unchanged |
| D. 03:00, stay awake | 02:00 -> 23:59 | 0 -> 4 (from 03:00) |
| E. 03:00, go back to sleep | 02:00 -> 23:59 | 0 -> 4 (from 10:30) |
| F. 00:30 + 450 min, 22:04 | 00:30 -> 23:59 | 0 -> 4 |
| G. 00:00 sleep, 20:00 | 00:00 -> 23:59 | 0 -> 4 |
| H, I. 23:30 controls | 23:30 | unchanged |
| J. No sleep anchor, 22:00 | 16:00 -> 23:59 | 0 -> 4 |
| K. No sleep anchor, 11:00 | 16:00 -> 23:59 | same placements |
| L. Nap + core sleep | 14:00 | unchanged (decision 4) |

- **End to end** with the real clock (2026-11-18, 02:44, inside the pilot's 02:00-10:30 sleep), in throwaway exports with the pilot's full Life Skeleton shape plus two tasks due today and two daily habits. The real `python modules/console.py today reschedule` ran, then `home_api._today()` (what Home shows) read the schedule file:
  - Before the fix, `sleep_policy:stay_awake`: the six fixed blocks only.
  - After, `stay_awake`: work from 02:44 (Email the landlord, Read a chapter, Evening stretch, Journal), then the fixed blocks; bedtime 02:00 tomorrow, plan to 23:59.
  - After, `sleep_policy:go_back_to_sleep`: work starts at 10:30.
  - After, a 04:00 bedtime still ahead (no prompt): work 02:44-03:59, plan stops at 04:00. The 20-minute habit that did not fit was left out.
  - Every run exited with the known segfault at exit (issue 3), including the before run; the schedule was written first.
- Home's view code is unchanged. Its input was checked through `home_api._today()`, not in a browser this time; no block ends at `00:00`, so nothing new reaches it.

## Limits

- **Nothing is planned past 23:59.** After midnight, re-plan: midnight to bedtime is planned as the new calendar day. Daily habits for the new date can then show up again after midnight (Chronos counts a habit done at 01:00 for the new date).
- **Template blocks authored after midnight** (a window at 00:30-01:30 before a 02:00 bedtime) are read as this morning, so they only take effect when planning after midnight.
- **Several sleep blocks** (decision 4): a 14:00 nap still ends the day at 14:00, and sleep blocks other than the one ending the day are not kept free of work (polyphasic: only one block counts). Tracked in `docs/ISSUES_AND_NEXT_STEPS.md`.
- **Future dates** (Kairos is only run for today in practice): a bedtime after midnight is always "tomorrow" there, and the morning part of sleep is not blocked, as before for every bedtime.

## Future: a day that lasts until bedtime

Not built (decision 2). The idea: for a night owl, 00:00-02:00 belongs to the day they are living, so the evening plan would run through midnight to bedtime, and Home, completions, habit streaks and commitment periods would keep counting it as "today" until bedtime or wake-up. The pilot's view: the day starts when you wake up and open Chronos.

Estimate given to the pilot: several steps, about the size of the whole status scale-down work. Chronos decides what "today" is in about 69 places in the Python code (calendar-date calls in `commands/`, `modules/`, `utilities/`), plus the dashboard's JavaScript:

- the `today` command;
- Home (`home_api._today`);
- the completion log (`mark`, `complete`, `did`, the timer) and habit streaks;
- commitment periods (`direction.py`);
- the listener;
- the Today and calendar widgets.

All of these need one shared "which day is it" rule. The scheduler would also need to place and store times past 24:00, with the placement code, `runtime.py`, Home and the Today widget reading minutes instead of `HH:MM` text (see "Why 'just make it 02:00 tomorrow' was not enough").
