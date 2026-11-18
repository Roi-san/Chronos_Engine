# Recurring items: how often, and on which day (decision D2)

Status: proposal 2026-11-18, approved by the pilot the same day ("go ahead with D2"). Decision B (spread) taken 2026-11-19. **Built and verified on 2026-11-19, committed in `0d0578a`**, as roadmap step 1c on `home-hub-fixes`. Fixes issue 10, and issues 22, 27 and 29 found on the way, in `docs/ISSUES_AND_NEXT_STEPS.md`. The [Build log](#build-log) at the bottom has every step in order.
The pilot on D2: "it should be flexible if possible ... maybe tie it to other features like the parameter weights, without going overboard ... if you have a good enough idea, go for it." This is that idea, with the reasoning, so it can be changed before it is built.

How to read this file: the sections from "The problem" to "Defaults chosen" are the proposal **as the pilot approved it, unchanged**, except for notes marked *(changed 2026-11-19)* where a later decision replaced a line. Everything decided after that, and the exact rule as built, is in the sections from [Decisions after the proposal](#decisions-after-the-proposal) on.

## The problem (issue 10)

`frequency` on a habit, chore or task says how often it repeats. Kairos only understands `daily` and weekday names (`kairos_v2._frequency_applies_to_date`):

- `weekly` is treated like `daily`: planned every day.
- `monthly`, `quarterly` and `yearly` match nothing: never planned.

The Chore Setup wizard writes exactly these values: 5 daily, 7 weekly (190 minutes together), 6 monthly, 4 quarterly and 4 yearly chores. Activate them and about 3 hours of weekly chores land on every day, while the other 14 never appear.

## What people need

One rule cannot fit everything, because recurring things are not all alike:

| Kind | Example | If it is missed |
| --- | --- | --- |
| Fixed-day ritual | Board game night on Tuesday; gym Monday, Wednesday, Friday | Gone until next time. Doing Tuesday's game night on Wednesday makes no sense. |
| Daily habit or chore | Wash the dishes, meditate | Tomorrow is a new day: no double portion. But a missed day means tomorrow's matters a bit more (the dishes pile up). |
| Once per period | Laundry weekly, wash windows monthly, change the air filter quarterly | Never lost. It stays until it is done, and gets more insistent as the period runs out. Once done, it is gone until the next period. |
| Several per period | Gym 3 times a week | That is a commitment; it already works this way. |

People differ too. Planners want a fixed day ("laundry is Saturday"). Flexible people want "sometime this week". Overwhelmed people need nothing to be lost and nothing to punish them. Some people want more pressure, some less.

## Proposal

### 1. Three rhythms, from values people already write

- **Weekday names** (`frequency: tuesday`, or a list): fixed days, as today.
- **`daily`**: every day. After a missed day, the next day's gets a small push: the same "missed last time" push commitments already get. Never a double portion.
- **`weekly`, `monthly`, `quarterly`, `yearly`**: once per period. Weeks run Monday to Sunday, as for commitments.

### 2. Once per period: a preferred day, then "until done"

- An optional **`day:`** on the item. For weekly items a weekday (`day: saturday`); for monthly items a day of the month (`day: 15`; a day the month does not have means its last day). Quarterly and yearly items have no preferred day at first: "sometime in the period".
- **With a day:** planned on that day. If it is missed, it stays on the plan every following day until it is done or the period ends. This is the pilot's "between A and C": a set day, and a missed one still comes back.
- **Without a day:** "sometime this period". It is in the pool from the first day of the period with low urgency, so it gets planned when a day has room.
  *(changed 2026-11-19, decision B: checked against the Chore Setup wizard, this put every undated chore on the first day of its period, a new wall of chores. Instead, Kairos gives each undated item its own day, spread evenly over the period, and it then follows the "with a day" rule. See [Decisions after the proposal](#decisions-after-the-proposal).)*
- **Done** (or its lighter version done, as for commitments): gone until the next period.
- **Period over and not done:** it starts fresh. No double portion next period, just the small "missed last time" push.

### 3. Urgency that grows, using what exists

- Same curve as commitment pressure (`modules/scheduler/direction.py`), from the days left in the period: on track 0.2, tightening 0.45, at risk 0.7, last chance 1.0.
- One new row in `user/settings/scheduling_priorities.yml`: **Recurring Pressure** (0-10, 5 neutral, 10 doubles it, 0 switches it off). That is the dial for how insistent recurring items get, next to Goal Alignment and Commitment Pressure.

### 4. Grace stays in charge

- Recurring pressure counts as **importance, never urgency**. On a tough day it can keep a chore when it matters enough (importance against strain, `status_scale_down_design.md`), but it never forces a chore through the way a deadline does.
- A chore's lighter version (`mini_of`) counts as done.

### 5. The Chore Setup wizard

- Weekly chores get a day picker. By default the wizard spreads them over the week (laundry Saturday, bathroom Wednesday, ...), so no single day gets a wall of chores.
- Monthly, quarterly and yearly chores default to "sometime in the period".
- *(changed 2026-11-19: with decision B, Kairos does the spreading for every item without a day, so the wizard does not spread on its own; two spreading rules would drift apart. The picker defaults to "Any day (Chronos spreads it)" and writes `day:` only when you pick one, for weekly and monthly chores. Also found while preparing: the wizard's built-in chores could not be created at all, see [Decisions after the proposal](#decisions-after-the-proposal), point 5.)*

### Examples

| Item | What happens |
| --- | --- |
| Laundry, `weekly`, `day: saturday` | Planned Saturday. Missed: back on Sunday as "last chance". Done Sunday: gone until next Saturday. |
| Wash windows, `monthly`, no day | From the 1st it waits with low urgency and is placed on a roomy day. Still not done near the end of the month: at risk, then last chance. |
| Wash the dishes, `daily` | Every day. Missed Monday: Tuesday's dishes get a small push. |
| Board game night, `frequency: tuesday` | Tuesdays only. Missed: gone until next Tuesday. |
| Gym, `weekly`, also in "3 workouts a week" | The commitment's push comes on top, as today. |

## How it fits the rest

- **One shared helper for days and periods** (`docs/ROADMAP.md`, "Where the risk of inconsistency really is"): today, the bounds of a day, week, month, quarter or year, and "was it done in this period" (item history, completion logs, lighter versions). Commitments move onto the same helper. The future "day that lasts until bedtime" (issue 9) then only changes "what is today" in one place.
- **Commitments** keep pushing their targets on top.
- **Free time** (decision D3): "sometime this period" items are what fills free time on light days; how many per day is part of that decision.
- **Home** (later): a "Still to do this week" list for recurring items not planned today, so nothing is invisible.
- **Habit streaks** for weekly or monthly items should count periods, not days (follow-up).

## Work, when built

| Part | Size |
| --- | --- |
| Shared period helper (move `period_bounds` and `_done_dates` out of `direction.py`; add quarter and year) | S |
| Recurrence check in Kairos with completion history, carry-over and the push | M |
| Recurring Pressure row and importance source | S |
| Chore Setup wizard: day picker and spread | S-M |
| Tests per rhythm and period, carry-over, push, weight 0, lighter version, commitment on top; before/after week dumps | part of the above |

## Defaults chosen (the pilot can change any of them)

1. A daily item gets a small push the day after a miss.
2. A missed preferred day comes back every following day until done (not just once more).
3. The field is called `day:`.

## Decisions after the proposal

| # | Question | Decision |
| --- | --- | --- |
| 1 | The proposal | Approved by the pilot on 2026-11-18 ("go ahead with D2"), with the three defaults above unchanged. |
| 2 | Items without a `day:` (asked 2026-11-19) | **B: spread them out.** The options put to the pilot: A, as written (every undated chore joins on the first day of its period and comes back daily until done: the wizard's 6 monthly chores, 3 hours, on the 1st of every month, and on 1 January 14 chores, about 8 hours); B, give each one its own day, spread over the period; C, only near the end of the period. The pilot: "most definitely B spread them out", "be EXTREMELY CAREFUL with that ... this is a key element in how things are scheduled. i dont want that to interfere with other things". |

Implementation choices, not asked (technical; the reason is given with each):

3. **No memory.** The pilot asked whether spreading means Chronos has to remember days. It does not: the days are worked out again on every plan, from the list of items, the same way every time. Nothing is stored that could get out of sync, and a plan for another day (`tomorrow`, a future week view) sees the same days. The cost: when an item is added, removed, renamed, paused or given a day in the middle of a period, the other undated items of that period can move to other days (see [Limits](#limits)). A remembered ("frozen") version could be added later on top of the same rule without rebuilding it.
4. **One spreading rule, in one place** (`modules/scheduler/recurrence.py`). The Chore Setup wizard does not spread on its own (the proposal's point 5 changed accordingly).
5. **The Chore Setup wizard could not create its built-in chores** (found 2026-11-19 while preparing the day picker; tracker issue 22). It copies `<name> _example` habits, which `alpha_v0.3` no longer ships (the old `main` had two of them, in `user/examples/Habits/`). The `copy` command prints "does not exist" and exits normally, and the dashboard counts any command that exits normally as a success (issue 23), so the wizard reported "Created N chores" while creating none. Fixed in this step: the wizard creates a chore from its own list when the example does not exist, and still copies the example when it does (the friend's path).
6. **Completion logs are read faster.** The daily logs (`user/schedules/completions/`) are parsed with PyYAML's fast C parser when it is installed (same results; the plain parser otherwise), and the folder is listed once instead of checking every date. Measured on the pilot's machine with 8 entries a day: the 62 days of logs commitments already read took 199-265 ms per plan (and per Home load) with the old parser, 28 ms with the fast one. Quarterly and yearly items need up to two years of logs: 730 days took 3 s with the old parser and 347 ms with the fast one. A text pre-check that skips logs not mentioning the items (75 ms for 730 days) was measured but left out for now: names in other alphabets, or with quotes, are escaped in some log files, so it could skip a real completion. It can be added later if the look-back gets slow (tracker issue 27).
7. **`day:` is read for weekly and monthly items only.** Quarterly and yearly items are always spread for now; a `day:` on them is ignored, and that is recorded.
8. **Commitments move onto the same helper**, both the scheduler side (`direction.py`) and the tracker (`modules/commitment/main.py`, behind the Commitments widget, `commitments check` and its triggers), for **where a period starts and ends** (and its key) and **which days count as done**. What changes in the tracker:
   - It used to count only an item's `completion_dates`, so a habit finished through Start day (the timer writes only the day's completion log) did not count toward its commitment there, while the scheduler counted it (tracker issue 24). Now a day on which the item (or its lighter version) is logged as completed, but missing from its `completion_dates`, adds one completion. A day in both places still counts once.
   - It counted against the real clock even when given another day (`get_commitment_status(c, today=...)`); it now uses the day it is given. Nothing in Chronos passes another day, so nothing changes in normal use.
   - `quarter` and `year` periods now work (the tracker counted all-time for them, the scheduler treated them as a week).
   - Unchanged on purpose: the tracker still counts **each completion** (two in one day count twice, which per-target counts such as "post 10 times a week" rely on), while the scheduler counts **days**. That difference is older than this step and is logged as tracker issue 28, not changed here. An unknown period still counts all-time in the tracker and as a week in the scheduler (also issue 28).
   - Habit streaks still miss Start-day completions (issue 24, open).
9. **An item added after its turn starts with its next turn** (found 2026-11-19 while preparing a month-long check, before anything was committed). With the spread, every chore has a turn, and the "missed: back every day until done" default meant that chores set up in the middle of a period were all "missed" at once: the wizard's 26 chores set up on Thursday 19 November 2026 would have put 14 once-per-period chores (4 weekly, 4 monthly, 2 quarterly, 4 yearly) on that day, each called "missed". That is the wall decision B exists to prevent, and calling a chore you just created "missed" is a punishment. So:
   - New items of the types Kairos plans (habit, task, routine, subroutine, microroutine, timeblock) record the day they were made, `created: YYYY-MM-DD`. Every way of making an item goes through `item_manager.generic_handle_new` (the console's `new`, the dashboard's POST /api/item, so wizards, Brain Dump, Home's capture, an AI), so it is stamped there. A `created` given by the caller wins.
   - A weekly to yearly item whose turn this period came **before** its `created` day waits for its next turn (state `starts_next_period`). Its turn on or after that day works as before, including "missed: back every day until done" (the pilot's default 2 is unchanged).
   - Items without `created` (made before this step, or by hand) work as before: a passed turn counts.
   - Daily and weekday items do not look at `created`.
   - This was decided without asking, as it only follows the pilot's own rules (no wall of chores, never punish); it is reported to the pilot and can be changed.

## The rule as built

### Rhythms

| `frequency` | Rhythm | On the plan | Extra push |
| --- | --- | --- | --- |
| `daily` | every day | every day | after a missed day, a small push (+0.2), if it was ever done before (a brand-new item gets none) |
| weekday names (`tuesday`, `monday, thursday`, or a list) | fixed days | on those days only | none: a missed day is gone until next time |
| `weekly`, `monthly`, `quarterly`, `yearly` | once per period | from its turn until done (below) | grows as the period runs out (below) |
| anything else (`biweekly`, `every 2 days`, ...) | not understood | never, as before | none; listed in `schedule.recurring.unrecognised` (issue 26) |

Case does not matter (`Daily`, `WEEKLY`). With several values, `daily` wins; then the first of `weekly`/`monthly`/`quarterly`/`yearly` (weekday names next to it are ignored and recorded); then weekday names.

Periods: a week runs Monday to Sunday (as for commitments); months and years are calendar months and years; quarters are January-March, April-June, July-September and October-December.

### Its turn

- **A day you picked** (`day:` on the item). Weekly items take a weekday (`saturday`, or `sat`); monthly items a day of the month (`15`; a day the month does not have means its last day, so `31` always means the last day).
- **No day: Chronos spreads them.** All active items with the same period and no usable `day:`, sorted by name, are spaced evenly over the period: number i of n (counting from 0) gets day `floor((i + 0.5) x days in the period / n)` of the period, counting from 0. If that day already holds an item with a picked day, it takes the nearest free day, earlier first. If every day is taken (more items than days), the nearest of the least busy days.
- An item keeps its turn after it is done, so doing one chore never moves another.

Worked out with the rule (the week of Monday 16 November 2026, November 2026, the fourth quarter of 2026, the year 2026):

| Items without a day | Their turns |
| --- | --- |
| 1 weekly | Thursday |
| 2 weekly | Tuesday, Saturday |
| 3 weekly | Tuesday, Thursday, Saturday |
| 4 weekly | Monday, Wednesday, Friday, Sunday |
| 7 weekly (the wizard's weekly chores) | one a day, Monday to Sunday, in name order |
| 6 weekly, plus laundry with `day: saturday` | one a day: the undated chore whose turn would have been Saturday moves to the nearest free day |
| 6 monthly (the wizard's) | the 3rd, 8th, 13th, 18th, 23rd and 28th (February 2027: 3rd, 8th, 12th, 17th, 22nd, 26th) |
| 1 monthly | the 16th |
| 4 quarterly (the wizard's) | 12 October, 4 November, 27 November, 20 December |
| 4 yearly (the wizard's) | 15 February, 17 May, 17 August, 16 November |

### When it is on the plan, and how hard it pushes

For a once-per-period item, on a given day:

1. **Done this period** (the item or its lighter version; its own history or a daily completion log): not on the plan until the next period, also when it was done before its turn.
2. **Before its turn:** not on the plan ("waiting").
3. **From its turn until done:** on the plan every day, pushed by the commitment curve on the days left in the period, today included: 3 or more spare days "on track" 0.2, 2 "tightening" 0.45, 1 "at risk" 0.7, 0 "last chance" 1.0.
4. **The previous period ended without it**, and it had been done at some point before: +0.2, at most 1.0 ("missed last time", as for commitments).
5. **The period ends without it:** it starts fresh on its turn in the next period. Never a double portion.

Example, a weekly chore whose turn is Thursday, never done: Monday to Wednesday not planned; Thursday on track (0.2), Friday tightening (0.45), Saturday at risk (0.7), Sunday last chance (1.0); next Thursday on track again, plus 0.2 if it had ever been done before.

### What the push does

- **Ranking.** Points = `24 x level x Recurring Pressure / 5`: on track 4.8, tightening 10.8, at risk 16.8, last chance 24, a daily item after a miss 4.8. Calibration: a chore on its last day ranks just above a task due today (+20) and just below a deadline today (+25); on track is a nudge like "due within 3 days" (+5).
- **The dial.** Recurring Pressure is a new row in `user/settings/scheduling_priorities.yml`: 5 neutral, 10 doubles, 0 switches the push off. With 0 the item is still planned on its turn; only the extra ranking and importance go.
- **Tough days.** In status scale-down it is one more importance source next to goal, commitment and priority (`level x Recurring Pressure / 5`). It is never urgency: it never keeps an item the way a deadline does, and it never opens a helper window.

### What you see

- **Home**, in a block's reasons: "Once a week: today is its turn." (spread) or "today is its day." (picked); "Once a week: missed its day (Saturday), last chance this week."; "Daily: missed yesterday.". A once-per-period item with 1 or 0 spare days gets the **at risk** / **last chance** tag commitments already get; when an item is also pushed by a commitment, the commitment's state wins.
- **The schedule file**: `schedule.recurring` lists every once-per-period item (its turn and where it came from, whether it is on the plan, its level and reason), daily items pushed after a miss, and frequencies Kairos does not understand. The decision log's notes for the candidate phase list the same in short.

## How it is built

| Where | What |
| --- | --- |
| `modules/scheduler/periods.py` (new) | The one shared helper for days and periods: `today()`, `normalize_period()`, `period_bounds()` (day, week, month, quarter, year), `previous_period_bounds()`, `period_length()`, `period_key()`, `completed_names_by_date()` (the daily completion logs), `done_dates()`. |
| `modules/scheduler/recurrence.py` (new) | The rules above: `parse_frequency()`, `preferred_day()`, `spread_turns()`, `evaluate()`, `load_recurring()`. No Kairos import. |
| `modules/scheduler/direction.py` | Its period and log functions moved to `periods.py` (the old names stay, pointing there); `load_direction()` reads the logs once for commitments and recurring items and returns the recurring result; recurring pressure is a third signal next to goal and commitment; `bonus_for()` adds its points. `is_strong()` unchanged. |
| `modules/scheduler/kairos_v2.py` | `build_candidate_universe()` asks the recurring result whether an item is on today's plan (if the history cannot be read: shown, never hidden); `_status_importance()` adds recurring; `schedule.recurring`; phase notes. `_frequency_applies_to_date()` stays as that fallback. |
| `modules/commitment/main.py` | Periods, period keys and completions from `periods.py`. |
| `utilities/dashboard/home_api.py` | Recurring reasons and state in `direction.by_name` (a commitment's state wins); the kept sentence when recurring importance kept an item ("keeping its rhythm matters more than the strain"); asks `periods.today()` what day it is. |
| `modules/item_manager.py` | `generic_handle_new` stamps `created: YYYY-MM-DD` on new habits, tasks, routines, subroutines, microroutines and timeblocks (decision 9); a `created` given by the caller wins. |
| `utilities/dashboard/wizards/chore_setup/index.js` | Built-in chores are created from the wizard's own list when the `_example` habit does not exist (issue 22; the copy is kept for when it does); custom chores are sent as `{type, name, properties}` (issue 29); only meaningful fields are sent; every chore is checked after it is made, and the status line names any that could not be made; a day picker for weekly and monthly chores ("Any day (Chronos spreads it)" by default); `created` on every chore; the custom-chore row laid out on two lines. |
| `user/settings/scheduling_priorities.yml` | The Recurring Pressure row (Order 8, Rank 5). |
| `scripts/regression/chores_month.py`, `chore_setup_check.js`, `chore_files.py` | New checks: four weeks with all 26 wizard chores; the wizard walked to the end in a real browser; what it wrote to disk. |

## Limits

- **Edits in the middle of a period** (adding, removing, renaming, pausing an item, or giving one a day) can move the other undated items of that period to other days (decision 3).
- **Night owls:** something done at 01:00 counts for the new calendar day, so a weekly chore done at 00:30 on a Monday counts for the new week (issue 9). When "a day that lasts until bedtime" is built, only `periods.today()` and the plan's date change.
- **An item whose turn is the last day of its period** (a Sunday chore) has no catch-up day in that period; missed, it comes back on its turn next period.
- **Quarterly and yearly items** cannot be given a day yet (decision 7).
- **Habit streaks** for weekly or monthly habits still count days, not periods, and miss Start-day completions (issue 24).
- **Home has no "still to do this period" list yet**, so an undated item is not visible before its turn.
- **Template children** are planned whenever their template is used, whatever their frequency (unchanged).
- **An item created in the middle of a period** whose turn has already passed starts with its next turn when it has `created` (decision 9). Items without `created` (made before this step, written by hand, or copied with `copy`, which keeps the original's date) count a passed turn as missed and are on the plan at once, with a low push.
- **Unknown frequencies** (`biweekly`, `every 2 days`, three-letter weekday names in `frequency`) are still never planned; they are only listed in the schedule file and the decision log (issue 26).

## Tests

All written before the code and run on the unchanged code first (106 new tests; 98 failed or errored before, 8 passed as controls).

| File | Tests | What it pins |
| --- | --- | --- |
| `tests/test_periods.py` | 24 | `today`; period names; bounds of day, week, month (every length), quarter, year; previous periods across year ends; lengths; keys (week, month and day keys equal the ones commitment files already store, checked day by day over a year); the completion logs (statuses, names from keys, the range, a broken file, a missing folder); done days from history, logs and lighter versions; the same answers as frozen copies of the old `direction.py` code. |
| `tests/test_recurrence.py` | 42 | Reading `frequency` (daily, weekdays, periods, order of precedence, values it does not understand); daily and weekday items give the same days as a frozen copy of the old `_frequency_applies_to_date`; `day:` for weekly and monthly items (and what is refused); the spread (1, 2, 3, 4 and 7 weekly items, monthly, quarterly, yearly, February, a picked day kept and not doubled, more items than days, same name of two types, the same answer on every day of the period); the push curve, done this period, last period, missed last time, brand-new items, the sentences; daily misses and fixed days; new items (decision 9); loading from every folder, paused and bad items, done from history, logs and the lighter version; unknown frequencies listed; inactive statuses equal to Kairos's. |
| `tests/test_kairos_v2_recurrence.py` | 23 | Through Kairos on real days: an undated weekly item from its turn until done; a picked day; done on its day, done early, done through Start day; the wizard's 7 weekly chores one a day; the wizard's chores set up on a Thursday (only that day's turn; 7 without `created`); a picked day not doubled; monthly spread; monthly, quarterly and yearly items planned on their turns; daily and weekday items unchanged; the push growing over the week (points 4.8, 10.8, 16.8, 24); the dial (10 doubles, 0 keeps the item without points); the daily push; importance, never urgency (kept on a low day at its last chance, saved when on track); no helper window; a commitment still bringing its target back; the lighter version; a template child unchanged; the record; history unreadable, shown anyway. |
| `tests/test_commitment_periods.py` | 9 | The commitment tracker: a Start-day completion counts; once when in both places; the lighter version's logged completion; a skip does not count; the day given is used; last week does not count; quarter and year; two completions on one day still count twice; keys unchanged. |
| `tests/test_home_api_recurrence.py` | 4 | Home: the recurring reason and state reach the block; a commitment's state wins; Home asks the shared helper what day it is; the kept sentence. |
| `tests/test_item_created.py` | 4 | `new` stamps `created` on the six plannable types, keeps a given date, leaves other types alone. |

The test `CommitmentTrackerAgrees` in `tests/test_kairos_v2_direction.py` still patches `_count_in_period` to pin the tracker to the fixture's week; the tracker no longer needs it (it uses the day it is given), so the patch now does nothing. Left as it is.

## Verification

- **Full suite** (throwaway export, as always without `tests/test_kairos.py`): **486 passed, 0 failed**. Before: 380 passed, 0 failed (the two clock-dependent tests of issue 21 pass after midnight).
- **The tests can fail.** Four deliberate breaks on a copy were caught: every undated chore on the first day of its period (10 tests failed), "done" forgotten (9), chores counted as urgent (1), no recurring points (3).
- **Fake-life dumps** (`scripts/regression/`): `status_week`, `status_matrix`, `fixed_week`, `plan_dump` and `fixed_week` with breathing room are identical to before. `rich_dump` differs only on Monday to Wednesday: its weekly "Read" habit is no longer planned before its turn (Thursday). With breathing room on, the 30 freed minutes let the 5-minute margin after the Morning Routine in, so Morning run starts at 08:05 on those days. Thursday to Sunday are identical.
- **The Chore Setup wizard in a real browser** (`scripts/regression/chore_setup_check.js`, headless Chrome, throwaway copy; six built-in chores kept, one custom weekly 20-minute chore added). Before: the wizard said "Created 7 chores. Skipped 0 existing." and only one file existed: the custom chore, saved as **daily** with no length and its real fields as text under `data`. After: "Created 7 chores." and seven correct files (Laundry weekly with `day: saturday`, Wash Windows monthly with `day: 15`, the custom chore weekly for 20 minutes, all with `created`). No page errors.
- **End to end with the real command**, on that copy with the wizard's chores, at 01:27 on Thursday 19 November 2026: `python modules/console.py today reschedule` exited 0. Planned: Wash Dishes only. Waiting: Laundry (its day, Saturday), Vacuum Floors (its turn, Friday, moved off Saturday because Laundry has it). Starting next period, not called missed: Clean the car (turn Tuesday), Wash Windows (the 15th), the HVAC filter (16 November), the smoke alarms (2 July). Then a weekly chore with `day: monday`, last done two weeks ago, was added and the day re-planned: Home's "Right now" (headless Chrome) showed it first, "Once a week: missed its day (Monday), 4 days left this week; missed last week too.", and Wash Dishes after a 5-minute margin.
- **Four weeks with all 26 wizard chores** (`scripts/regression/chores_month.py`, set up on Monday 16 November 2026; the fake user does everything planned except Laundry on 18 and 19 November and Vacuum Floors all of the first week): at most 2 once-per-period chores on any day (35 to 90 minutes of them), never none. Laundry, skipped on its turn, came back on Thursday and Friday (on track, then tightening) and was done. Vacuum Floors came back as "at risk" and "last chance", then started fresh the next Saturday with no double portion. Every weekly chore was done every week from its first full week; monthly chores fell on the 18th, 23rd and 28th of November and the 3rd, 8th and 13th of December; the quarterly HVAC filter on 27 November; the smoke-alarm test on 16 November (its turn was the setup day); the chores whose turn had passed at setup were left for their next period.
- **Speed:** reading 62 days of completion logs, done on every plan and every Home load, went from 199-265 ms to 28 ms with the fast parser.

## Build log

- 2026-11-19 00:50. Baseline on a throwaway export of `7acaa59`: full suite 380 passed, 0 failed (after midnight, so issue 21's two clock-dependent tests pass); seven fake-life dumps saved for the before/after comparison.
- 2026-11-19 ~00:55. Decision B and the rule written down here, before any test or code. Found while preparing: issues 22-28 (logged in the tracker when the step is finished).
- 2026-11-19 ~01:05. Tests written first, run on the unchanged code (throwaway export of `7acaa59` plus the new test files): 96 new tests, 91 fail or error, 5 pass. `tests/test_periods.py` (24) and `tests/test_recurrence.py` (37) error out because their modules do not exist yet; `tests/test_kairos_v2_recurrence.py` 19 of 22 fail; `tests/test_commitment_periods.py` 7 of 9 fail; `tests/test_home_api_recurrence.py` 4 of 4 fail. The 5 that pass are controls for behaviour that must not change (daily and weekday items, no helper window, a template child, a skip in the log is not a completion) plus "last week does not count for this week", which passes on the old tracker only because it counts against the real clock.
- 2026-11-19 01:15. Code written: `periods.py`, `recurrence.py` (new); `direction.py`, `kairos_v2.py`, `commitment/main.py`, `home_api.py`, `scheduling_priorities.yml` (changed). The 96 tests pass; full suite 476 passed, 0 failed. To check that the tests can fail, four deliberate breaks were tried on a copy (every undated chore on day 1; "done" forgotten; chores counted as urgent; no recurring points): 10, 9, 1 and 3 tests failed. Fake-life dumps: `status_week`, `status_matrix`, `fixed_week`, `plan_dump` and the breathing-room `fixed_week` identical; `rich_dump` (and with breathing room) differ only on Monday to Wednesday, where its weekly "Read" habit is no longer planned (its turn is Thursday; before, every day). With breathing room on, the 30 freed minutes let the 5-minute margin after the Morning Routine in, so Morning run starts at 08:05 instead of 08:00 on those days. Thursday to Sunday identical.
- 2026-11-19 ~01:20. Found while preparing a month-long check: setting chores up in the middle of a period put every chore whose turn had passed on the plan at once, marked "missed" (the wizard's chores set up on Thursday 19 November 2026: 14). Fixed as design decision 9 (below, in "Decisions after the proposal"): new items record `created`, and a turn before it does not count. 10 more tests (7 failed before). New tests now 106, full suite 486 passed, 0 failed; the dumps are unchanged by it (the fake lives have no `created`).
- 2026-11-19 ~01:25. The Chore Setup wizard walked to the end in headless Chrome on the unchanged code: it said "Created 7 chores" and made one wrong file (issues 22 and 29, found while preparing the day picker). Fixed (creation from the wizard's own list, the right request shape, only meaningful fields, a check after each chore, the day picker); the same walk afterwards made seven correct files. The custom-chore row was too narrow for the new picker (the frequency box was already squeezed before), so it is laid out on two lines.
- 2026-11-19 01:27-01:34. End to end with the real `today reschedule` on that copy; Home's "Right now" in headless Chrome; four simulated weeks with all 26 wizard chores (`chores_month.py`; a bug in the script's own skip list was found and fixed on the way, not in Kairos). Details in [Verification](#verification). Docs updated next.
