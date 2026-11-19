# What the user sets, what Kairos reads: one model for planning and tracking

Status: **D5, D6, D7 decided and built 2026-11-19 (`5566407`); D8 and D9 decided 2026-11-19 and built 2026-11-20 (`a5c0f63`); D10 and D11 open.** (First written as a proposal waiting for D5 to D11.) Written 2026-11-19 ~22:40 after the pilot asked to "think of the system as a whole and Kairos as the backbone always, such that we don't overlook a detail on how things are scheduled", and "I don't want mismatching to happen anywhere". Nothing in this document is built yet. Evidence: tracker issues 38 to 45 and the checks in `docs/WORKLOG.md` (2026-11-19 entries).

## The problem in one sentence

The planner itself is mostly sound. The holes are where **what the user sets** (in a wizard, a builder, Home's capture box) **is not what Kairos reads**, or is read differently by different parts of Chronos.

## Three rules for every fix from now on

1. **Meaning comes from what the user set, never from words in a name.** A "Bedtime Routine" and an "Evening Wind-down" with the same steps are the same thing and must be planned the same way. Kairos may only treat something specially because of a field the user (or a wizard on their behalf) set on purpose: its type, where it sits (on the day template, anchored), or an explicit mark.
2. **Every place the user can create something writes the same shape, and that shape is what Kairos reads.** If a habit can repeat "3 times a week" in one place, it can in all of them; if Kairos reads `frequency`, every form that makes a habit offers it. A field Kairos does not read is not offered as if it did something.
3. **One record of what happened, one interpreter, every screen reads it.** Done, Skip and "not done by the end of its turn" are written once (the daily completion log) and interpreted once (`modules/scheduler/periods.py`, `recurrence.py`, `direction.py`). Streaks, commitments, goals, Home, points and the scheduler ask that interpreter; none keeps its own count. (This is roadmap step 3, "one way to record a completion", issues 24, 4, 28, 30.)

## Map: each concept, where the user sets it, what Kairos reads

| Concept | Where the user sets it today | What Kairos reads | Mismatch |
| --- | --- | --- | --- |
| **Sleep** | Life Setup (Core Sleep: `category: sleep`, `tags: [sleep]`), Sleep Settings wizard (`sleep: true`) | Any item whose name contains "sleep" or "bedtime", or with category/tag sleep or `sleep: true` (5 copies of this rule: `kairos_v2._is_sleep_like_node`, `kairos_v2._looks_like_sleep_entry`, `sleep_gate._is_sleep_anchor`, the tray app) | #38: a routine called "Bedtime Routine" is never planned. #43 (new): the Sleep Settings wizard's own wind-down pack ("Digital Sunset", "Blackout Setup", "Last Meal Buffer") is marked `sleep: true`, so it is never planned either. The mark means both "this is my sleep" and "this is about sleep". |
| **Which day template today** | Day Builder (status requirements; days only through the Extra box); the console's `today reschedule template:"Name"` | Status fit first, then alphabetical; the console choice for that one run only | #40, #16: there is no way to choose in the dashboard, a choice is not remembered on the next re-plan, and a Weekend template loses to a general one on Saturday. |
| **When** (a time for an item) | Only the day template (Day Builder, Life Setup) | Only the day template | #42 (new): an item's own time is ignored for every type. A daily "Meditate" habit with `start_time: 21:00` (also tried `ideal_start_time`, `time`) is planned at 08:35. Home's capture box has no time field; the Routine Builder has none for the routine itself. |
| **How often** | Habits: Home capture (always daily, from `habit_defaults.yml`), Chore Setup (frequency and day). Routines: nowhere. Tasks: due date. | `frequency` (D2: daily, weekdays, weekly to yearly, spread over the period), due date, deadline, goal and commitment pushes | #41a: "3 a week" commitment habits are daily. #39: a routine not on a day template is never planned. |
| **Done / Skip** | Home's Done and Skip (`mark`), `complete`, `did`, Start day (the timer), the Yesterday check-in | The daily completion log and items' `completion_dates`, read by several pieces in different ways | #24, #4, #28, #30 (step 3). #44 (new): a milestone completed by hand gives no points and fires no `on_complete` triggers. |
| **Goal progress** | Goal Planning (milestones with a text measure and "key steps" text), the Milestones widget (Complete button) | Milestone `criteria` as a count or a checklist (a dict), computed in `modules/milestone/main.py`; goal % = weighted milestone %, computed in three places | #41b: Goal Planning's measures are text, so no milestone ever moves by itself; key steps never become tasks. (#41c and #41d fixed 2026-11-19, `19353dc`.) |

## Proposals and the decisions they need

### A. Sleep is a block on your day, nothing else (D5) · size S

**What changes.** "Is this my sleep?" gets one shared rule in one helper (used by Kairos, the sleep gate, the tray app and the completion-log reader):

- Only a **fixed block on the day template** can be sleep: an anchored timeblock marked `sleep: true`, or with category or tag `sleep` (what Life Setup and Sleep Settings already write).
- **Anything else is ordinary work, whatever its name, category or tags**: habits, routines, microroutines, tasks. "Bedtime Routine", "Evening Wind-down", "Sleep Hygiene - Digital Sunset" are all planned like any routine.
- A day template that has **no marked sleep block** (an old or hand-written one) falls back to an anchored *timeblock* whose name contains "sleep", and the plan says so on Home ("Treated 'Night sleep' as your sleep because nothing on the day is marked as sleep. Mark it in the Day Builder."). This keeps every existing template working, and the fallback can never catch a routine or a habit.
- The completion log: an entry counts as sleep only if it is that sleep block (by name) or carries `sleep: true`. Today, completing "Bedtime Routine" would be counted as sleep minutes.
- Later, separately: a wind-down item may want "just before bedtime" as its time. That is part of C ("when"), not of the sleep rule.

**D5. Decided 2026-11-19: (a)**, the pilot: "go with your gut here, based on what you know about the project". **Built** the same night (see Build log). Found while building: the Sleep Settings widget's own sleep blocks were not sleep for Kairos (#46), fixed by the same rule. The question was: (a) as above, with the name fallback only for anchored timeblocks and a visible note; (b) the same without any fallback: an unmarked "Sleep" block stops being sleep, and Kairos uses the bedtime from your sleep settings and says so. **Recommendation: (a).** It is name-independent for everything you build, and old templates keep working. Your real day template (`life_skeleton.yml`) has `category: sleep` and `tags: [sleep]`, so either option keeps it as sleep.

### B. You choose today's day template, and Kairos remembers it (D6) · size S-M

**How it works today, precisely.** You do not pick a template anywhere in the dashboard. Every time the day is planned (Plan my day, Re-plan, Start day), Kairos picks one itself:
1. only templates allowed on today's weekday (`days`, if set);
2. the one whose `status_requirements` are closest to how you said you feel (Home's status, the Sick day button);
3. on a tie, the alphabetically first name.

So a "Perfect Day" is chosen when your status says excellent health and high energy, a "Sick Day" when you press Sick day, and otherwise the closest or first by name. The only way to say "today is a Perfect Day" is the console (`today reschedule template:"Perfect Day"`), and the next Re-plan from Home forgets it. That is the gap: **your choice has nowhere to live.**

**What changes.**
- Home gets a **"Today is: [Auto ▾]"** picker listing your day templates. Auto keeps today's behaviour (status, then name).
- The choice is saved for that date in the day's manual-changes file (`schedules/manual_modifications_<date>.yml`, which every re-plan already re-applies), so Re-plan, Start day and a restart keep it. Tomorrow starts on Auto again (see D6b).
- Kairos records "Today's template: Perfect Day (your choice)" or "(closest to how you feel: ...)" and Home shows it, so you always see why.
- On a tie, a template that names today's weekday beats one that names no days (so "Weekend" wins on Saturday). The Day Builder gets a Days field instead of the Extra box.

**D6. Decided 2026-11-19: yes to both** (D6a and D6b), the pilot. They do not need to pick a template in the dashboard for now ("maybe in the future a drop-down menu for super handy usage"), so the picker is **not built**; what was built: the weekday tie-break, `days: []` = any day, and the choice explained on Home (see Build log). When the picker comes, D6a and D6b apply.

**D6a. The question:** when you pick a template, does your status still lighten single items (status scale-down: a "Gym" swapped for "Home mobility" when you are ill)? **Recommendation: yes.** You choose the shape of the day; the forgiving rule for single items stays. Choosing "Sick Day" is the way to make the whole day lighter.
**D6b. Decision:** is the choice for today only, or "until I change it"? **Recommendation: today only**; a lasting choice is better expressed with the template's `days` (Weekend: Saturday and Sunday).

### C. "When" and "how often" become fields of every item, read the same way (D7, D8) · size M

**What changes.** Every repeatable item (habit, routine, chore, task) can carry the same two fields, offered in every place that creates or edits it (Home's capture box, Brain Dump, Chore Setup, the Routine Builder, Goal Planning's habits):

- **How often**: the D2 `frequency` that habits and chores already use (daily, weekdays, weekly to yearly, with an optional day). Nothing new in the engine; routines simply get it too, and Home stops making every habit daily (it offers the choice, default daily).
- **When** (new): optional. Either a time ("21:00") or a part of the day: morning, afternoon, evening, **before bed** (the last free time before your sleep block). Parts of the day come from your wake and sleep times, so they move with a night owl's day.

Kairos then places a timed item **at its time if that time is free, otherwise as close as possible inside the same part of the day, otherwise anywhere**, and records which (Home: "21:00 was taken by Dinner, planned at 21:30").

A routine that is **on the day template and also has a frequency** is planned once: the template's slot wins that day. The day template stays the place for fixed blocks (work, sleep, appointments).

**D7. Decided 2026-11-19: a wish**, the pilot: "a wish yes. Appointments should be locked in place obviously" (appointments: #17, and fixed library items #47). **Built** the Kairos part the same night (see Build log); the time fields in the forms come with D8.

**D7. The question:** is an item's own time a wish (it moves when the slot is taken, as above) or a fixed appointment (it blocks the time like a template anchor)? **Recommendation: a wish.** Fixed things belong on the day template, or later as appointments (#17); a wish keeps the day forgiving and visible.
**D8. Decided 2026-11-19: yes.** The pilot wrote "the answer is 8. the most intuitive answer"; read as yes, the recommended and most intuitive option (say so if that was not meant). **Built** with the parts of the day and the form fields (see Build log, 2026-11-20).

**D8. The question:** is "before bed" a part of the day of its own? **Recommendation: yes.** It is exactly what a wind-down or bedtime routine needs, and it follows the sleep block wherever it is.

### D. One record of Done, Skip and missed (D9, D11) · size M · roadmap step 3

This is step 3 of `docs/NEXT_SESSION.md` ("one way to record a completion", issues 24, 4, 28, 30), and it must come before goal progress and streaks build on history. What it adds to that step:

- **One function records an outcome** for every path (Home's Done and Skip, `complete`, `did`, Start day, the Yesterday check-in, a milestone's Complete button): it writes the daily log entry, the item's history, points (D-step-3a: once per item per day), and then runs the follow-ups (commitments, milestones, achievements).
- **Skip today means "not today"**, as it does now: closed for today, not counted as done, back tomorrow with a little more push (weekly and longer items stay due until done, D2; a commitment's push grows). Never a penalty, never double.
- **Not done by the end of its turn** (a daily habit at midnight, a weekly chore at Sunday night) is recorded as missed by that same interpreter, so streaks, commitments and Home agree about it.

**D9. Decided 2026-11-19: yes** (the pilot: "also a yes if you think you can do that"). **Built** (see Build log, 2026-11-20). One call that follows from the pilot's rules, open to veto: the skip wins for the period, so a goal, commitment or due date does not bring the item back before its next turn.

**D9. The question:** should a weekly or longer item also offer **"Skip this turn"** (not this week: comes back next week, no push), next to "not today"? **Recommendation: yes, as a second button only on items that repeat weekly or less often.** "Not today" stays the default.
**D11. Decision:** when you finish a routine, do its steps count as done (a "Read a book" habit inside the routine keeps its streak and counts for its commitment)? **Recommendation: yes**, each step counts once, and "Skip" on the routine skips its steps for today.

### E. Goals measure themselves from what you do (D10) · size S-M

**What changes.**
- **Goal Planning's measure becomes choosable, not free text.** A milestone is done when: (1) **N times** a habit or task you pick, in a period ("Run 12 times"), or (2) **all its key steps** are done, or (3) **by hand** (the Complete button). These are the count and checklist shapes `modules/milestone/main.py` already computes.
- **Key steps become real tasks**, linked to the milestone and its goal, so they come into the plan through the goal's push, and finishing them moves the milestone (checklist).
- Completed by hand means 100% (fixed 2026-11-19), and gives the milestone's points and triggers (with D).
- Goal % stays "weighted average of its milestones", computed in **one** function used by `track goal`, the Goal Tracker and the dashboard lists (today three copies).

**D10. Decision:** should Goal Planning turn each key step into a task automatically? **Recommendation: yes, with a checkbox per step** (on by default), undated, linked to the goal. An undated task with no goal would never be planned (#13); with the goal link it is.

## Order (proposal)

| # | What | Size | Needs | Why here |
| --- | --- | --- | --- | --- |
| 1 | A. Sleep is a block on your day | S | D5 | Small, independent, and it unblocks bedtime routines and the wind-down pack today. |
| 2 | B. Today's template: picker, remembered, weekday tie-break | S-M | D6a, D6b | Independent of the rest; answers "I picked Perfect day". |
| 3 | D. One record of Done / Skip / missed (step 3) | M | D9, D11, and step 3's (a), (b) | Goals, streaks and commitments must read one history before more is built on it. |
| 4 | E. Goals measure themselves | S-M | D10 | Builds on D. |
| 5 | C. "When" and "how often" everywhere | M | D7, D8 | Touches placement, the most delicate part of Kairos; done with the full set of fake-life regression dumps, after the rules above have settled. |

Each step follows the usual way of working (`docs/START_HERE.md`): tests first, a throwaway copy, before/after fake-life dumps, the real commands, a headless browser for dashboard parts, results checked on disk.

## Build log (2026-11-19, ~22:50-23:25)

All in a throwaway export first, tests before code (failures recorded), full suite, the fake-life dumps and probes before and after, the real `today reschedule` on a copy of the pilot's day template, Home in headless Chrome. Committed as `5566407` (code) on the pilot's go, ~23:40.

- **A (D5).** New `modules/scheduler/sleep_blocks.py`: `is_marked_sleep_block`, `is_named_sleep_block`, `template_sleep_blocks` (marked blocks, else named fixed ones), `uses_name_fallback`, `is_sleep_block_of`, `is_sleep_log_entry`. Kairos: `commit_anchor_skeleton`, the template-children candidates, library candidates, `_effective_length`, `_find_sleep_anchors`, `_looks_like_sleep_entry` (+ `_sleep_block_names`) use it; `_is_sleep_like_node` removed; `_record_sleep_blocks` writes `schedule.sleep_blocks`. `sleep_gate._is_sleep_anchor` and `_walk_sleep_anchors` use it. Tests: `tests/test_sleep_blocks.py`, 13 (13 failed before). Behaviour that changed on purpose: see the tracker's Done row. Left: #48.
- **B (D6), without the picker.** `select_day_template`: `selection_key` with the weekday step; `_template_names_weekday`; `_explain_template_choice` writes `schedule.day_template_choice`. `v1.is_template_eligible_for_day`: `days: []` is any day. `home_api.day_template_line` and `plan_notes`; Home's Today card shows the template line and the notes. Tests: `tests/test_template_choice.py`, 9 (9 failed before).
- **C (D7), the Kairos part.** `_normalize_candidate` keeps `wished_time`; `_place_wished_times` in `populate_day_and_windows` turns free wishes into timed slots and records every wish in `schedule.wished_times`; `home_api.plan_notes` says when one moved. Tests: `tests/test_wished_time.py`, 10 (9 failed before; the tenth, "not its day means not planned", guards unchanged behaviour). One test was wrong at first (it wished 12:00, inside Work, while planning the whole day); corrected to plan from now, as `today` does.
- **Results.** Full suite 536 passed, 0 failed (23:18). `rich_dump`, `status_week`, `status_matrix`, `fixed_week`, `plan_dump`, `chores_month`, `sleep_probe`, `routine_probe`, `gap_probe`: identical before and after (no fake life had an own-time item or a name-only sleep rule that changed).

## Build log (2026-11-19 ~23:40 to 2026-11-20)

- **D8, parts of the day.** New `modules/scheduler/day_parts.py` (`parse_when`, `window`, `latest_first`, `label`, `PART_LABELS`). Kairos: candidates keep `when`; `_place_wished_times` takes clock times (`start_time`, or `when: "21:00"`) first, then parts; `_free_slot` finds the first free stretch of a part, or the last one for before bed; `_wake_minutes` is the end of the day template's main sleep block (07:00 without one); bedtime is `day_budget.sleep_boundary_minutes`. Rows in `schedule.wished_times` carry `wished` ("21:00", "the evening", "just before bed"), `placed`, `why` and `at`. Home's note now reads "X was meant for ..., but ..." for both D7 and D8.
- **Forms.** Home's capture box: When (task, habit) and How often (habit); the Routine Builder: How often and When, written on every save (`set` merges, so an empty value clears an older one) and loaded with the routine.
- **D9, Skip this week.** `commands/mark.py` (`skip:period`, also from the console), `periods.turn_skips_by_date` (one shared log loop, `_names_by_date`), `recurrence.evaluate(..., skipped=...)` and `evaluate_library(..., skipped_by_date)`, `direction.load_direction`, Kairos (`skipped_turns`, `schedule.recurring.skipped_this_period`), `home_api.turn_periods` and a plan note, Home's button.
- **How it fits the rest.** Template windows count as busy for part wishes (#49). Before bed follows where the plan ends, so for a night owl it is before 23:59 until issue 9 (#50). A skipped turn is not a completion, so the coming "one record of Done / Skip / missed" (step 3) keeps it as its own outcome. Template members are structure: a routine placed on the day template is not removed by a skipped turn of its library copy.
- **Found by the browser walk and fixed before the commit.** When and How often carried over to the next capture (now reset after Add); a part of the day after where tonight's plan ends was placed after bedtime (parts are clipped to the plan's end); a clock time after bedtime was described as "running into" it (now "is after bedtime, where this plan ends").
- **Results.** Tests: 13 + 13 new, plus one in the D7 file (all new behaviour failed before; 3 guard unchanged behaviour); full suite 563 passed, 0 failed; the nine fake-life dumps and probes identical; the headless-Chrome walk (see the tracker's Done row).

## Log

- 2026-11-19 ~22:40: first version, after the pilot's questions about bedtime routines, Perfect / Sick day templates, "how often / when", skips and goal progress. Evidence gathered the same evening (tracker 38 to 45). Waiting for D5 to D11.
- 2026-11-19 ~23:25: the pilot decided D5 ("go with your gut": (a)), D6 (yes, yes; no picker for now), D7 (a wish; appointments locked in place). A, B (without the picker) and the Kairos part of C built the same night; see Build log. Open: D8 to D11.
- 2026-11-20: D8 ("the most intuitive answer": yes) and D9 (yes) built with the form fields; see Build log. Open: D10, D11.
