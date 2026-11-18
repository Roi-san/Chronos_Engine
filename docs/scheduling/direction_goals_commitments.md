# Goals and commitments in scheduling

Status: prototype on branch `home-hub`. Code: `modules/scheduler/direction.py`, wired into `modules/scheduler/kairos_v2.py`. Tests: `tests/test_kairos_v2_direction.py`.

Kairos used to rank work by category, priority, due date, deadline and happiness. Goals, milestones and commitments were tracked but never read by the scheduler. They are now two more ranking factors, and they can also bring an item onto the day that nothing else would.

## What it does

1. **Brings work into scope.** A task or habit that serves an active goal, or that an unmet commitment counts, becomes a candidate even with no due date and on days its own frequency would skip.
2. **Ranks it higher.** The closer a goal's date, and the closer a commitment is to being missed, the bigger the push.
3. **Opens a helper window** ("Commitment Window", "Goal Window") when the pressure is strong and the template has no place for the item.
4. **Scales down when the day does not fit.** If the full version needs energy or health you do not have today, and you authored a lighter version, Kairos schedules the lighter one. It still counts toward the commitment.

## How to set it up

| You want | Write this |
| --- | --- |
| A task or habit to serve a goal | `goal: <goal name>` on the item. Also read: the goal's `supporting_habits`, a milestone's `criteria` / `links`, and a task's `project` when the project has a `goal`. |
| A commitment the scheduler can act on | `rule: {kind: frequency, times: 3, period: week}` and `targets: [{type: habit, name: Gym session}]`. Period is `day`, `week` (Monday to Sunday), `month`, or since 2026-11-19 `quarter` or `year` (periods come from the shared helper `modules/scheduler/periods.py`). |
| A lighter version | `mini_of: Gym session` on the lighter item (or `mini_variant: Home mobility` on the full one). |
| "The full version needs a good day" | `status_requirements: {energy: [high, medium], health: [excellent, good]}` on the full item. |

The Home page's capture box has fields for the first three. Status requirements are set with the Status Mapping wizard or in the item's YAML.

## Commitment pressure

For a frequency commitment Kairos looks at how many are still to do and how many days are left in the period, counting today.

`slack = days left - still to do`

| Slack | State | Level |
| --- | --- | --- |
| 3 or more | on track | 0.2 |
| 2 | tightening | 0.45 |
| 1 | at risk | 0.7 |
| 0 | last chance: needs one every remaining day | 1.0 |
| below 0 | behind: cannot fully catch up | 1.0 |

- **After a miss:** if the previous period ended unmet, the level rises by 0.2 until the current period is met. This applies only when there is history from before the current period, so a brand-new commitment is not treated as missed.
- **Met:** no push at all.
- **Interchangeable targets** ("gym or run, 3 a week"): only as many as today needs get the full push; the others stay at 0.2.
- **What counts as done:** the target's `completion_dates`, the daily completion logs, and completions of its lighter version. Since 2026-11-19 the commitment tracker (`modules/commitment/main.py`: the Commitments widget, `commitments check` and its triggers) reads the same logs, so a completion made through Start day, which is only written to the log, counts there too (issue 24). The tracker still counts completions while the scheduler counts days (issue 28).
- **Recurring items** (weekly to yearly habits and chores) get their own push with the same curve, from `modules/scheduler/recurrence.py`; when an item is also a commitment target, both apply. `docs/scheduling/recurrence_design.md`.

## Goal pressure

`level = 0.35 x priority weight + closeness`, capped at 1.0.

| Priority | Weight | | Days to the date | Closeness |
| --- | --- | --- | --- | --- |
| high, urgent, critical | 1.0 | | overdue or today | 0.65 |
| medium, normal | 0.6 | | 1 to 3 | 0.55 |
| none | 0.5 | | 4 to 7 | 0.4 |
| low | 0.3 | | 8 to 14 | 0.25 |
| | | | 15 to 30 | 0.12 |
| | | | later, or no date | 0 |

The date used is the nearest of the goal's own date and the date of the milestone the item belongs to. Completed, archived, cancelled and on-hold goals push nothing.

## Points

`bonus = 60 x goal level x (Goal Alignment rank / 5) + 90 x commitment level x (Commitment Pressure rank / 5)`

The ranks are two rows in `user/settings/scheduling_priorities.yml`. 5 is neutral, 10 doubles the push, 0 switches the factor off.

The maxima were calibrated against real scores with the shipped settings: due today is +20, deadline today +25, the top category about +42, top priority +20, so a high-priority work task due today scores about 66.

| Situation | Bonus |
| --- | --- |
| Commitment, last chance or behind | 90: outranks any ordinary task due today |
| Commitment, at risk | 63 |
| Commitment, tightening | 40 |
| Commitment, on track | 18 |
| High-priority goal due within 3 days | 54 |
| High-priority goal, no date | 21 |
| Low-priority goal, no date | 6 |

The bonus is added in `_urgency_bonus`, which every scoring path already calls (window selection, gap fill order, helper windows, quick wins, and the trim/cut ranking), so an at-risk commitment is also the last thing cut when the day overflows.

## Scaling down

Superseded in detail by `docs/scheduling/status_scale_down_design.md` (2026-11-17). In short, in `_scale_down_for_status`, after the one-way status fit of each candidate is known:

- an item that today falls short of (worse than the worst value it accepts; better than needed is never a mismatch) and that has an authored mini no more demanding than itself is replaced by the mini, even if the mini is short too;
- the mini inherits the goal and commitment pressure of the item it replaces;
- a mini is never scheduled next to its own full version;
- with no mini, the item stays when it is within grace, urgent, or its goal/commitment/priority importance outweighs the strain; otherwise it is saved for a better day.

Goal and commitment pressure therefore do two jobs: they rank work (above), and they decide whether an item is kept on a day that does not fit it. The swaps are recorded in `reality_filtered_candidates.scaled_down`, everything status did in `schedule.status_scale_down`, and the Home page says "Lighter version of ... It still counts."

`modules/commitment/main.py` now counts a mini's completions toward the commitment too, so the tracker and the scheduler agree.

## What is recorded

`schedule.direction` in the day's runtime file: every goal with its date, every commitment with its state, and each pushed item with its reason and bonus.

## Limits

- ~~A full version with a fixed slot in the day template is not swapped.~~ Fixed since 2026-11-17 (`docs/scheduling/status_scale_down_design.md`, step 2): a "Gym 18:00" slot becomes its lighter version at 18:00 on a day that does not fit, or is freed.
- **Lower status is the only trigger.** There is no notion of "the gym is closed" or "I am travelling" beyond the status dimensions, and `place` is not used in the fit calculation yet (Kairos defers it).
- **"Never" commitments** ("no doomscrolling") are not scheduled; there is nothing to place.
- **Nothing happens when a period ends unmet** apart from the extra push next period. See below.
- **A goal with nothing linked to it** changes nothing. The Home page shows "nothing linked yet" on such goals.
- **Appointments** still do not block time. They need to be added to the day as anchored timeblocks.

## Rewards and consequences today

What exists:

- **Points.** Completing something earns points by type (`user/settings/points_settings.yml`: task 10, habit 5, routine 5, milestone 15, goal 100). `points balance` shows them.
- **Rewards.** Items with a cost and a cooldown; `redeem reward "<name>"` spends points.
- **Achievements.** Awarded for milestones and streaks; they give XP and levels.
- **Commitment triggers.** A commitment can list actions under `triggers.on_met` and `triggers.on_violation`: run a script, create a reward, create an achievement. They fire on `commitments check`, once per period.

What does not exist:

- **No penalty.** Nothing ever removes points on its own. `points subtract` exists as a command, so a script under `on_violation` could do it.
- **A missed frequency commitment is never a "violation".** Only `never` commitments (you did the forbidden thing) and manual overrides violate. When a "3 a week" ends at 2, the tracker simply starts the new week; no trigger fires.

The smallest useful addition would be a `triggers.on_missed` list plus an optional `miss_penalty: <points>` on the commitment, fired once when a period closes unmet. `direction.evaluate_commitment` already computes `missed_previous`, so the check is there to reuse.
