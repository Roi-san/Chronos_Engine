# Road to a usable Chronos: strategy and order of work

Status: agreed by the pilot on 2026-11-18. D1 decided and built (step 1a done, committed). Step 1b done. D2 decided (2026-11-18, with option B on 2026-11-19) and step 1c built, verified and committed (`0d0578a`) on 2026-11-19. Phase 1 is complete. D3 and D4 come later.
This file says in what order to work and why, and what to watch so later features fit without rework.
`docs/ISSUES_AND_NEXT_STEPS.md` is the tracker: every known problem with its number and status. Numbers below (#10, #12, ...) are tracker numbers.
Every fact here was checked against the code on 2026-11-18 (`home-hub-fixes`); code references are given so it can be re-checked.

## The goal

Chronos is used every day by the pilot and a few friends. "Used" means the daily loop works without surprises:

1. **Set up once** (fresh install): onboarding, Life Setup (sleep, meals, work), chores, habits, goals, commitments, status.
2. **Capture** during the day: Home's quick capture, Brain Dump, the console, an AI.
3. **Plan**: Kairos builds the day from what you have and how you feel.
4. **Do**: Home's "Right now", Done/Skip, Start day (the timer).
5. **Look back**: the next day's check-in, trackers, commitments.

First fix whatever breaks or lies in that loop. Build new features on top only after.

### "Usable" means all of these are true

- Everything you capture shows up: on a day's plan, or in a list Home shows. Nothing silently never appears.
- Chores and habits appear on the right days and as often as they say.
- Appointments and fixed commitments block their time.
- A day's plan never ends early or empties for a reason you cannot see.
- Start day runs work as work and breaks as breaks.
- No control in the dashboard is a switch that does nothing.
- A friend can go from a fresh install to a planned day without help.

## Rules that keep it seamless

1. **One source of truth per idea.** Anything two features need (what day it is, whether something was done this week, how long an item is) lives in one function that both call. Two copies drift apart, and that is where inconsistencies come from.
2. **Forgiving by default, strict only by choice** (the pilot's philosophy): keep things visible, never punish, give grace. Every rule that could feel strict gets a setting.
3. **Ask on philosophical choices.** The pilot decides with options and a recommendation; nothing of that kind is guessed.
4. **Prove every change.** Tests written first (they must fail before the fix), the full suite (345 passed, 0 failed on 2026-11-18; 486 passed, 0 failed with step 1c on 2026-11-19; so any failure is new), before/after plan dumps of fake lives for scheduler changes, and a run of the real command.
5. **Write it down in the same commit.** Tracker, design doc and reference docs change with the code. Every bug or inaccuracy found gets a tracker number, even if it is not fixed.

## Kairos v1 and v2: what is what

There have been three schedulers. Only one runs.

| Scheduler | Where | State (checked 2026-11-18) |
| --- | --- | --- |
| Pre-Kairos inline scheduler | The bottom half of `commands/today.py` ("dormant inline legacy pipeline", `build_initial_schedule` and the conflict phases) | Unreachable. `docs/documentation_overview.md`, section 2, describes it. |
| Kairos v1 | `modules/scheduler/kairos.py`, `weekly_generator.py`, `verify_kairos.py` | Archived by the friend when v2 arrived: these three files are now stubs that only raise an error. The full v1 is still in git history: `git show b1b0bb2:modules/scheduler/kairos.py` (2026-03-15, 3781 lines, with its buffer, break and sprint logic), useful when porting a v1 feature. The friend also keeps an archive on their own computer (`META/LEGACY_SCHEDULING`, never committed). |
| **Kairos v2** | `modules/scheduler/kairos_v2.py` (added 2026-03-19) | **The live scheduler.** All work on this branch builds on it. |

So there is no second scheduler to choose between; v1 is leftovers. What is left of it in the repository: the three stubs, `tests/test_kairos.py` (tests v1, so it cannot pass and is left out of the suite), `user/settings/scheduling_priorities_legacy.yml`, the old docs (now marked out of date), and options that `today` and the Today widget still send (#11).

### What v1 did that v2 does not do (yet)

These are the "missing buffers, breaks, sprints" (#11).

| v1 feature | What v2 has instead | Recommendation | Size |
| --- | --- | --- | --- |
| Buffers inserted into the plan (`buffers:`) | Breathing room (`buffer_settings.yml`), the v2 version of the same idea | Make the toggle switch breathing room on or off for one re-plan | S |
| Timer breaks inserted into the plan (`breaks:`), long blocks split into sprints (`sprints:`) | Nothing. By design the timer should do this (`timer_owns_execution_shaping` in the timer handoff), but in Start day the timer runs each block as one stretch (`modules/timer/main.py`, `start_schedule_plan`); profile focus/break lengths are only used when you start the timer by hand | Build it in the timer: split long blocks by the chosen profile's focus and break lengths (#18) | M |
| Quick-wins limit per re-plan (`quickwins:N`) | Quick wins run from `quick_wins_settings.yml`; the per-run limit is not read | Wire it | S |
| Trend influence (`ignore-trends`) | No trend input at all (a placeholder, `_gather_trend_inputs`) | Hide the switch until trends exist; trends are a later feature | L (feature) |
| Status match threshold | Replaced by the one-way fit with Grace (`status_scale_down_design.md`) | Hide it; Grace is the control | S |
| Per-run weights (the sliders, `prioritize:`) | Weights live in `scheduling_priorities.yml`; `prioritize:` only steers which day template is chosen | **Decision** (later): relabel the sliders as template preferences, or make them override the weights for one re-plan | S / M |
| Dependency order (`depends_on`) | None | Later, if wanted; routines already keep order | M |
| Week skeleton (`today kairos week`) | Disabled | Later (week planning) | L |
| `auto_inject`, `essential`, `environment`, legacy status keys | `today inject`, `cut: allow` / `trim: allow`, place (deferred) | Nothing to do | - |

**Do these first or last?** They can safely wait. They sit at the edges: the Today widget, the option parser in `commands/today.py`, and the timer. None of Kairos's core decisions (what gets into the day, when, how status and goals weigh) depend on them, so doing them later causes no rework. Most are either already replaced by something better in v2 (Grace, breathing room) or wait on a feature that does not exist yet (trends). The one real missing feature is breaks inside long blocks, and it belongs to the timer, not the scheduler. The cheap part (wire two switches, hide three) can happen any time; it is planned for phase 4.

## Where the risk of inconsistency really is

1. **Days and periods.** "What day is it" is worked out from the calendar in about 69 places (`docs/scheduling/sleep_after_midnight.md`, "Future"). Commitments have their own week and month logic (`modules/scheduler/direction.py`: `period_bounds`, `_done_dates`, `evaluate_commitment`). Weekly and monthly chores (#10) need exactly that logic, and the future "day that lasts until bedtime" (#9) changes what "today" means for all of them. If each feature keeps its own copy, they will disagree (a chore done at 01:00 counted on different days by streaks, commitments and Home).
   → Build #10 on one shared helper: the current day, the current period, and "was it done in this period" (lighter versions count, as for commitments). Move commitments onto the same helper. The bedtime project later changes only that helper.
   → **Done in step 1c (2026-11-19):** `modules/scheduler/periods.py` (`today`, period bounds and keys for day to year, the completion logs, done days with lighter versions). Commitments (scheduler and tracker) and recurring items use it. Still outside it: the period code in `commands/review.py` (#25), the about 69 places that read the calendar date directly (they move with the bedtime project, #9), and how commitments count (completions or days, #28).
2. **Free time.** Light days (pack or spread), undated tasks (#13), "fill freed time with what suits the day", quick wins and breathing room all decide what happens with free time. As separate rules they would fight: a day spread out for breathing room filled back up with backlog tasks.
   → Decide them together as one free-time policy, implemented in one place (gap fill and the final spacing pass, `_apply_breathing_room`).
3. **An item's length.** Kairos checks for a positive duration in seven places in `kairos_v2.py`. A default length has to be applied once, where candidates are normalised, so every later phase sees the same length. Containers (a routine with steps) must keep "no length", so their steps are still placed one by one (`docs/scheduling/builder_templates_prototype.md`).
4. **Routines as one block (#15).** Breathing room, status scale-down and the timer all treat a routine as one item. Showing its steps touches all three, so do it after their rules have settled.

Starting #10 now does not get in the way of the switches above. It touches recurrence and completion history, which none of them use.

## The biggest obstacles to smooth scheduling (2026-11-19)

Written after phase 1, at the pilot's request; kept up to date in `docs/NEXT_SESSION.md`, which also gives the order to tackle them.

1. **Unknown breakpoints** (phase 2): parts of the daily loop nobody has walked to the end, and a dashboard that reports a failed command as done (#23).
2. **Appointments do not block time** (#17).
3. **Free time** (D3): light days are packed from now; tasks without a date are never planned (#13).
4. **Completions are recorded in four ways** (#24, #4, #28, #30): fix once, before building on history.
5. **What "today" is for a night owl** (#9), now one function in `modules/scheduler/periods.py`.
6. **Routines as one block, no breaks in long blocks** (#15, #18).

## Order of work (proposal)

| Phase | Step | Tracker | Size | Needs |
| --- | --- | --- | --- | --- |
| 1. Nothing silently missing | 1a. A default length for items without one. **Done 2026-11-18** (`docs/scheduling/item_lengths.md`) | #12 | M | D1 |
| | 1b. Tests for habits (a safety net before touching recurrence). **Done 2026-11-18** (`65355e2`) | next task 3 | S-M | - |
| | 1c. One shared day/period helper; weekly, monthly, quarterly, yearly done properly; commitments moved onto the helper. **Done 2026-11-19 (`0d0578a`)** (`docs/scheduling/recurrence_design.md`). Found and fixed on the way: the Chore Setup wizard created none of its chores (#22, #29). | #10 | M | **D2** |
| 2. Find the unknown breakpoints | 2. Fresh-install walkthrough as a new friend, in a throwaway copy with a headless browser: onboarding, Life Setup, Chore Setup, Brain Dump, Goal Planning, plan, Start day, the next day's check-in. Every problem gets a tracker number, then is placed in phase 3 or 4. | new | M | - |
| 3. The day looks right | 3a. Missed fixed-time items (a morning routine showing up in the afternoon) | #14 | S | D4 |
| | 3b. One free-time policy: light days, undated tasks, quick wins | #13, next task 2 | M | D3 |
| | 3c. Appointments block their time | #17 | M | - |
| 4. Honest controls and execution | 4a. Today widget: wire buffers and quick wins, hide what v2 replaced | #11 | S | - |
| | 4b. Timer: breaks inside long blocks in Start day | #18 | M | - |
| | 4c. Routine steps on Home and in the timer | #15 | M-L | - |
| | 4d. Small: Yesterday Check-in (#7), points twice (#4), template choice (#16) | #7, #4, #16 | S each | decisions |
| 5. Night owls and sleep | 5. A day that lasts until bedtime, naps | #9, #8 | L | - |
| Later | Fill freed time with what suits the day; move a slot later; numeric status weights; a trigger when a commitment period ends unmet; Claude as Nia's AI; trends; week planning; v1 clean-up (#19, with the friend); changelog and docs housekeeping; field names (the friend's call) | | | |

Why this order: phase 1 fixes things that are wrong today and that everything else builds on (lengths, recurrence, days). Phase 2 finds what nobody has hit yet, before more is built on top. Phases 3 and 4 make the day right and the controls honest. Phase 5 is the biggest change to how days work, done last on the shared helper from 1c.

## Decisions

| | Question | Options | Recommendation |
| --- | --- | --- | --- |
| **D1** | What happens to an item with no length (#12)? | (a) Give new items a default when they are created; old items stay unplaceable. (b) When planning, give any leaf item without a length a default (a setting, 30 min), and mark the block "length not set, planned as 30 min". (c) Both, plus a length field in Brain Dump. | (c): nothing captured is lost, old items included, and you can see and fix the guess. **Decided 2026-11-18: (c), default 30 min as a global setting.** On routines the pilot added: "a placeholder for the things inside it", never left out, so a routine without its own length is planned for the total of its steps. |
| **D2** | What do `weekly`, `monthly`, `quarterly` and `yearly` mean for a habit or chore (#10)? It is about how often an item repeats, not the week template. Today `weekly` lands on every day and the others on none. | (a) A day you pick ("laundry: saturday"); (b) once per period until done: it shows every day until you do it, then disappears until the next period; (c) a preferred day, and if missed, it stays visible each following day until done. | (c): it keeps the order of a set day and the grace of "until done". A missed chore is never lost, never punished, and never shows twice in a week. **Proposal 2026-11-18** (the pilot: "between A and C", "flexible", "tie it to the weights"): `docs/scheduling/recurrence_design.md`. **Decided:** the proposal (2026-11-18), and for items without a day option B, spread them over the period (2026-11-19: "most definitely B"). Built 2026-11-19 with one addition, decision 9: an item added after its turn starts with its next turn. |
| D3 | Free-time policy (phase 3) | Options in `docs/scheduling/gaps_and_breathing_room.md` ("Open decision: light days"), plus: may undated tasks fill free time, and how much? | Decide in phase 3. |
| D4 | When does a missed fixed-time item come back (phase 3)? | Never; until a cut-off time (e.g. 12:00); or a per-item setting with a default | Decide in phase 3. |

## Log

- 2026-11-18: first version, after the pilot asked for a strategy before more fixes. Written from the open list given in chat; the chat's "#5" (tasks created without a length) is tracker #12.
- 2026-11-18: the pilot agreed with the plan and D1. Step 1a built and verified (365 passed, 0 failed). Found while doing it: a routine without its own length vanished from the plan with its steps; now fixed by the same rule. D2 written up as a proposal for the pilot's go; next: step 1b (habit tests), then 1c.
- 2026-11-18: step 1b done (`65355e2`); the pilot gave the go for D2 as written. The session then hit its usage limit before 1c started.
- 2026-11-19: before building D2, checking it against the Chore Setup wizard showed that items without a day would all join on the first day of their period (6 monthly chores, 3 hours, on the 1st; 14 chores on 1 January). The pilot chose option B: spread them. Step 1c built and verified: 106 new tests, full suite 486 passed, 0 failed, a real browser walk of the wizard, the real `today reschedule`, and four simulated weeks with all 26 wizard chores (at most 2 once-per-period chores on a day). Found on the way and logged: #22-#30 (#22, #27, #29 fixed in the same step). Committed as `0d0578a` on the pilot's go. Next: phase 2 (the fresh-install walkthrough), on the new branch `usable-chronos`. The pilot asked to work small things first and to build so nothing needs rebuilding.
