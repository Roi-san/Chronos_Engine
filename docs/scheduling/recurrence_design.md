# Recurring items: how often, and on which day (decision D2)

Status: **proposal**, 2026-11-18. Not built. Fixes issue 10 in `docs/ISSUES_AND_NEXT_STEPS.md` when built, as roadmap step 1c (`docs/ROADMAP.md`), after the habit tests (step 1b).
The pilot on D2: "it should be flexible if possible ... maybe tie it to other features like the parameter weights, without going overboard ... if you have a good enough idea, go for it." This is that idea, with the reasoning, so it can be changed before it is built.

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
