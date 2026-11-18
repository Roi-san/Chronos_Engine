# Gaps and breathing room

Status (branch `home-hub-fixes`, 2026-11-18): **implemented**, except "light days", which is an [open decision](#open-decision-light-days). Fixes issue 2 in `docs/ISSUES_AND_NEXT_STEPS.md`. Code: `modules/scheduler/kairos_v2.py` (`_runtime_helper_settings`, `_breathing_room_settings`, `_apply_breathing_room`, `_space_items`). Tests: `tests/test_kairos_v2_gaps_and_breathing_room.py`.

## The problem

Issue 2, found 2026-11-17: at 22:05, with Gym fixed at 22:30, a 20-minute task with a deadline today went to 23:15, after the gym, although 22:05-22:30 was free.

The pilot's first read (2026-11-18): leaving the gap could be smart, since "theres is almost Always time lost between transitioning or lost in wrong estimation". Measuring showed Kairos was **not** leaving room on purpose.

**Why it happened.** Urgent work goes into a Kairos-made *helper window* ("Deadline Window", "Due Window", "Commitment Window", "Goal Window", "Manual Opportunity Window"). Urgent here means due today, a deadline, a strong goal or commitment push, or added by hand. Helper windows were only opened in gaps of **30 minutes or more** (`runtime_helper_windows.minimum_gap_minutes`, default 30), so urgent work jumped over smaller gaps to the next big one. Ordinary work has no such rule. It fills any gap, highest score first, earliest gap first, with no margin at all.

**Kairos left no breathing room anywhere.** Everything was packed back to back and right up to fixed blocks. The archived v1 scheduler did insert breaks ("Phase 4: Final Buffer Insertion": a dynamic buffer after continuous work, and buffers after routines). Its settings are still in `user/settings/buffer_settings.yml` and the Day and Routine Builders show them, but Kairos v2 loaded them and never used them.

### Measured before the fix

Scratchpad probe `gap_probe.py` (fixture day, sleep 23:55, `start_from_now` as Home's Re-plan does):

| Case | Result |
| --- | --- |
| 22:05, Gym 22:30-23:15, 20-min task with deadline today | task 23:15-23:35, after the gym |
| same, task due today | 23:15-23:35 |
| same, a 20-min daily habit instead | habit 22:05-22:25, right away |
| deadline task + daily habit | habit takes 22:05; the **deadline** task waits until 23:15 |
| deadline task, no gap of 30+ minutes later (Gym until 23:40) | task 22:05-22:25 (so the rule was never about room) |
| 08:35, 25-min gap before a 09:00 meeting, report due today | report 13:30-13:50, five hours later |
| light day, 11:00, three habits, afternoon free | 11:00-11:15, 11:15-11:45, 11:45-12:15, nothing after |

## Decisions (pilot, 2026-11-18)

| # | Question | Decision |
| --- | --- | --- |
| 1 | Urgent work and small gaps | **Earliest gap it fits.** Urgent work takes the first free gap it fits in and is never pushed later than ordinary work. |
| 2 | Breathing room | **5 minutes, only where there is room.** Use the existing setting's 5 minutes after each item and before a fixed block; if a task only fits without it, place it anyway. Breathing room never costs a task. |
| 3 | Light days: pack from now, or spread out? | **Open decision, documented below; nothing built.** |

## The rules

### Urgent work takes the earliest gap

`_runtime_helper_settings`: the default minimum gap for a helper window is now 1 minute (`RUNTIME_HELPER_DEFAULT_MIN_GAP_MINUTES`). Gaps are visited in time order, so a helper window opens in the first gap where urgent work fits. Work that fits nowhere earlier still goes to a later gap. Setting `runtime_helper_windows: {minimum_gap_minutes: 30}` in `scheduling_settings.yml` brings back the old behaviour.

### Breathing room

Settings: `user/settings/buffer_settings.yml`:

```yaml
global_dynamic_buffer:
  buffer_duration_minutes: 5   # the margin
  buffer_interval_minutes: 5   # minutes of continuous work that earn one
```

With no `global_dynamic_buffer` section, breathing room is off. A missing key inside the section takes the v1 default (5 minutes, 45-minute interval). The shipped file and the pilot's own file have 5 and 5, which means a margin after every item of 5 minutes or more. `template_buffers` (per-type buffers after routines) are still not applied by Kairos v2.

How it works (`_apply_breathing_room`, run when the conceptual blocks are built, after every placement, relief and quick-win pass):

1. **What is planned does not change.** Placement runs exactly as before; this step only moves work later inside its own free stretch, using slack the day already has.
2. **Work in an emergent gap** (gap fills, quick wins, Kairos helper windows) can get a margin:
   - after a fixed block, when the stretch follows one;
   - between two items, once `interval` minutes of work have run without a break;
   - before the next fixed block.
   Fixed blocks are anchors, fixed-time slots, authored windows, and free and buffer blocks.
3. **Work inside an authored window, free or buffer block** gets margins between items and stays inside the block.
4. **The first item after "now" starts now.** Nothing moves earlier, nothing goes past the end of its stretch, and only whole margins are added.
5. **Not enough slack for every margin:** the one before a fixed block comes first (getting to the gym), then those between items in time order, then the one after a fixed block.
6. **No slack:** nothing moves. A 25-minute task in a 25-minute gap before the gym still goes there.

Recorded in `schedule.breathing_room`: `minutes`, `interval_minutes`, `source`, `margins_added` (margins that moved work), `margins_before_fixed_blocks` (kept free, nothing moved), `items_moved`. The conceptual blocks, the timer's execution units, the schedule file and Home all get the spaced times. The internal placement records (`remaining_structure_placement`, `post_relief_layout`, `quick_wins`) keep the packed times from before this step.

Worked examples (5/5):

| Case | Plan |
| --- | --- |
| 11:00, lunch 13:00, Journal 15 + Read 30 + Walk 30 | 11:00-11:15, 11:20-11:50, 11:55-12:25 |
| 22:00, Gym 22:30, two 10-min habits | 22:00-22:10, 22:15-22:25 (5 min before the gym) |
| 22:00, Gym 22:30, two 12-min habits (room for one margin) | 22:00-22:12, 22:12-22:24 (the margin before the gym wins) |
| 14:30, Work until 15:00, a 20-min habit | 15:05-15:25 |
| 22:05, Gym 22:30, 25-min deadline task | 22:05-22:30 (fits only without the margin, so it goes in) |
| 10-min margin after 45 min of work | Journal 11:00-11:15, Read 11:15-11:45, Walk 11:55-12:25 |

The Day Builder's own "Auto Buffers/Breaks" tool reads the same file and writes buffer blocks into the template when you build it. Kairos treats those as authored buffer blocks: it fills them with overflow, adding margins between items inside them, and never moves them.

## Open decision: light days

Not decided, nothing built (decision 3). The pilot's words: "perhaps sometimes u dont [have a full day] in which case u dont want Kairos to cramp unnecessary things together if theres a lot more free time before or after".

What Kairos does today: it fills free time from "now" (or from the start of each gap), earliest first, and leaves all leftover time at the end of each gap. Breathing room adds 5 minutes between items, but a light day still bunches its work at the start of the free time (three habits done by 12:25, an empty afternoon).

The dilemma:

- **Packing from now helps you start.** Home's "Right now" always has something to do, which matters for task starting (the reason Chronos exists). Free time stays in one block at the end, which reads as "done for today".
- **Spreading out is less cramped** and leaves room for overruns and real breaks, but it can leave you idle between tasks and lose momentum. "Next up in 1h 40m" is an invitation to drift.

Options for later:

1. **Leave as is** (pack from now, with breathing room).
2. **Spread evenly**: when the day has far more free time than work, share the spare time out between items, maybe capped (no more than N minutes between items).
3. **Times of day**: give items a preferred time of day (morning, evening) and place them there when the day allows.
4. **Follow energy**: place demanding items where today's energy is expected to be highest. This needs an energy curve, which Chronos does not have.
5. **A user setting**: "pack" vs "spread", or a density level, maybe per day template ("a slow Sunday").

Any of these goes in the same place as breathing room (the final spacing pass), since that already only moves work inside its free stretch. Options 1, 2 and 5 are small; 3 and 4 need new item fields or data.

## What changed

All in `modules/scheduler/kairos_v2.py`:

| Where | Change |
| --- | --- |
| module constants | `RUNTIME_HELPER_DEFAULT_MIN_GAP_MINUTES = 1` (was 30, inline); `BREATHING_ROOM_DEFAULT_MINUTES = 5`, `BREATHING_ROOM_DEFAULT_INTERVAL_MINUTES = 45`. |
| `_runtime_helper_settings` | Uses the new default; an explicit setting still wins. |
| `_build_conceptual_blocks` | Window blocks carry `runtime_helper` (Kairos-made or authored); runs `_apply_breathing_room` before sorting and the remaining-day filter. |
| `_breathing_room_settings` | New: reads `global_dynamic_buffer`. |
| `_apply_breathing_room` | New: the spacing pass above; works on copies of the placed children; recomputes the span and name of gap fills, quick wins and helper windows ("Gap Fill 11:00-12:25"). |
| `_space_items` | New: lays out one stretch with whole margins from its slack, in the priority above. |

## Tests

`tests/test_kairos_v2_gaps_and_breathing_room.py`, 19 tests, written before the code: **13 failed, 6 passed**. The 6 were controls (the explicit 30-minute setting, a task that does not fit, breathing room off without the setting) plus one case whose layout is the same before and after. After the code, 19 passed; one test's expected list was corrected because I had left out the Lunch anchor, which is also a timer unit.

| Class | What it pins |
| --- | --- |
| `UrgentWorkTakesTheEarliestGap` (6, breathing room off) | Deadline and due-today tasks before the gym; the report before the 09:00 meeting; urgent work gets the early gap before ordinary work; work that does not fit goes later; `minimum_gap_minutes: 30` still works. |
| `BreathingRoom` (13) | Between items, before and after fixed blocks, the first item starts now, only-fits-without, priority when room is short, never changes what is planned (three days compared on vs off), authored windows, custom minutes and interval, off without the setting, the gap fill's span and name, the timer units and the schedule file, the `breathing_room` record. |

## Verification

- **Full suite** (fresh export): **333 passed, 2 failed**. 333 = 314 + 19 new; the 2 failures are the known upstream ones (timer break-as-buffer, TRICK debug-console registry).
- **Regression dumps** with breathing room off (the test fixture has no `global_dynamic_buffer`): `rich_dump`, `status_week`, `status_matrix`, `fixed_week`, `plan_dump` are **byte-for-byte identical** to before. None of those fake lives had urgent work skipping a smaller earlier gap, so the urgent-work change only shows where the bug happens.
- **Breathing room on** (5/5) for the rich week and the fixed-slot week: on every one of 14 days, **the same items** are planned. 31 items in the rich week moved later by whole margins, with no overlaps between items and none with fixed blocks. Tight stretches kept their single spare margin before the next fixed block (06:00-07:25 before a 07:30 routine), and full stretches did not move (08:00-09:00).
- **End to end**, real `today reschedule sleep_policy:stay_awake` at 03:17 on 2026-11-18, throwaway export, the shipped `buffer_settings.yml` (5/5). Core Sleep 02:00-10:30, Gym fixed 25 minutes ahead (03:42), a 20-minute deadline task, two daily habits; read back through `home_api._today()` (what Home shows):
  - Before: Evening stretch 03:17-03:37, Gym 03:42, File taxes 04:27-04:47 (after the gym), Journal 04:47.
  - After: File taxes 03:17-03:37 (before the gym), Gym 03:42-04:27, Evening stretch 04:32-04:52, Journal 04:57-05:12.
  - Both runs ended with the known exit segfault (issue 3) after writing the schedule.

## Limits

- Margins are whole (5 minutes or nothing); 3 spare minutes stay at the end of the stretch.
- Whether a margin between two items is allowed is decided assuming every earlier margin was taken. With the shipped interval of 5 this changes nothing.
- `template_buffers` (after routines, subroutines, microroutines) are not applied.
- Steps inside a routine placed as one block are not spaced; the routine is one item.
- Home shows the margins as free time. During one, "Right now" says "Next up in 5 min".
