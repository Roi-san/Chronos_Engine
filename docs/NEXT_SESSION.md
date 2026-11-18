# Next session: read this first

Written 2026-11-19 ~01:50 for the next person or AI session that picks up this repository. It says where things stand, what to do next and in what order, the biggest obstacles to smooth scheduling, and how the pilot wants the work done. Update it at the end of every session (replace "Where things stand" and "Do next"; keep the rest unless it is wrong, and say what you changed in `docs/WORKLOG.md`).

## Where things stand

- **Branch `usable-chronos`** (new on 2026-11-19, at the pilot's request: "a lot of things changed"). It starts from `home-hub-fixes` at `b1f223e`, which is pushed and holds everything up to and including roadmap phase 1. Do all new work here. `home-hub-fixes` and `home-hub` stay as they are (history of the earlier work; `docs/HOME_HUB_HANDOVER.md` describes them for the friend). Nothing is merged upstream; the friend reviews later.
- **Roadmap phase 1, "nothing silently missing", is complete:** items without a length are planned (D1, `969cabb`), habit tests (`65355e2`), recurring items weekly to yearly with one shared day/period helper (D2, `0d0578a`). `docs/ROADMAP.md`.
- **Full suite: 486 passed, 0 failed** (run it after midnight or before 22:30: two tests in `tests/test_timer_anchor_wait.py` fail between 22:30 and midnight, issue 21). Any other failure is new.
- **The pilot's real data** (in `user/`, ignored by git) is small: one day template (`life_skeleton.yml`, Core Sleep 02:00-10:30) and three tasks. No habits, chores, goals or commitments yet. The pilot is likely to set up chores next with the Chore Setup wizard, which works since `0d0578a`.

## Do next, in this order

The pilot (2026-11-19): "first tackle the small things and build in a way that won't have to rebuild later. rather move slower than redo". Check in with the pilot after each numbered step; commit and push only when they say so.

| # | What | Size | Needs the pilot |
| --- | --- | --- | --- |
| 1 | **Fresh-install walkthrough** (roadmap phase 2): a throwaway export as a brand-new friend would meet it; onboarding, Life Setup, Chore Setup, Brain Dump, Goal Planning, Routine Builder, Home, plan a day, Start day, the next day's check-in, all in headless Chrome, **walked to the end** and checked on disk, not by what the screen says (issue 23). Every problem gets a tracker number. Do this first: on 2026-11-19 the Chore Setup wizard turned out to create none of its chores while saying it had, and nobody had walked it to the end before. | M | no |
| 2 | **Small batch:** #21 (fixed clock in the timer test), #25 (`commands/review.py` onto `modules/scheduler/periods.py`), #26 (Home shows chores whose frequency Chronos does not understand), #11 (Today widget toggles: wire buffers and quick wins, hide what v2 replaced). | S each | no |
| 3 | **One way to record a completion** (#24, #4, #28, #30): Home's Done (`mark`), `complete`, `did`, Start day (the timer) and the Yesterday check-in each write different things today (log only, item history only, points or not). One shared function, used by all of them, before anything else builds on history (streaks, stats, rewards). | M | yes: (a) points once per item per day? (#4) (b) commitments count days or completions? (#28) |
| 4 | **The day looks right** (phase 3): a missed fixed-time item (a morning routine showing up at 15:30, #14, decision D4); one free-time policy for light days, tasks without a date (#13) and quick wins (decision D3); appointments block their time (#17). | S, M, M | D3, D4 |
| 5 | **Honest execution** (phase 4): breaks inside long blocks in Start day (#18); a routine's steps on Home and in the timer (#15); template choice (#16); Yesterday check-in (#7). | M, M-L, S, S | #16, #7 |
| 6 | **Night owls** (phase 5): a day that lasts until bedtime (#9), naps (#8). Since step 1c this changes `periods.today()` and the plan's date, not every caller. | L | yes |

## The biggest obstacles to smooth scheduling (as of 2026-11-19)

1. **Unknown breakpoints.** The daily loop has parts nobody has walked to the end (wizards, alarms and reminders, `tomorrow` / `this` / `next`). Worse, the dashboard reports a console command as done whenever it exits normally, even when it printed an error (#23), so a button can say "done" for a failure. Until the walkthrough (step 1 above), we do not know how many such holes there are.
2. **Appointments do not block time** (#17). A doctor's appointment is ignored by the plan unless it is added to the day template as an anchored block. This is the biggest gap between the pilot's real life and the plan.
3. **Free time.** Kairos packs a light day from "now" (an empty afternoon after three habits by 12:25), and a task without a due date, deadline, goal or commitment is never planned at all (#13). Light days, undated tasks, quick wins and breathing room must be decided together as one policy (D3, `docs/scheduling/gaps_and_breathing_room.md`), implemented in one place (the final spacing pass), or they will fight each other.
4. **Completions are recorded in four ways** (#24, #4, #28, #30). Points can be given twice, streaks miss Start-day completions, and commitments are counted as completions by the tracker but as days by the scheduler. Everything that reads history inherits this, so fix it once (step 3 above) before building on it.
5. **What "today" is for a night owl** (#9). Plans stop at 23:59; something done at 01:00 counts for the next day (and for the next week on a Sunday night). The fix is big but now has one place to live (`modules/scheduler/periods.py`).
6. **Routines are one block** (#15) and **long blocks have no breaks** in Start day (#18): fine for planning, rough for doing. They wait until the rules above settle, because breathing room, status scale-down and the timer all treat a routine as one item.

## How the pilot wants the work done

- Read, in this order: this file, `docs/START_HERE.md` (philosophy, where code lives, the checklist for every change, testing recipes, gotchas), `docs/ROADMAP.md`, `docs/ISSUES_AND_NEXT_STEPS.md`, the end of `docs/WORKLOG.md`, and the design doc of whatever you touch (`docs/scheduling/`). If the pilot asks whether you have the context, also read the last session transcript (JSONL files in the Claude projects folder for this repository) before saying yes.
- **Philosophy:** Chronos is a kind, outsourced planner for someone who struggles with starting and switching tasks. Forgiving by default, strict only by choice; keep things visible (seeing and skipping beats not seeing); never punish (missed things come back with a little more push, never double); usable first. Philosophical choices are the pilot's: offer options with a recommendation, write the answer down. A choice that only follows from their rules can be made, but say so plainly and let them veto it.
- **Extremely careful; document every action.** Tests first (record how many fail before), the full suite in a throwaway export (never in the repo's `user/`, the pilot's real data), before/after fake-life dumps (`scripts/regression/`), the real command end to end, a headless browser for dashboard changes, and check results on disk. Keep a build log in the design doc while working and an "IN PROGRESS" work-log entry for a big step, so a cut-off session leaves a trail.
- **Do not delete documentation silently.** Keep approved text; mark what changed inline with a date; when something must go, say exactly what in the work log.
- **Commits:** code first, then the docs with the code's hash. Push after each commit, when the pilot says so. Log timestamps from the real clock (`date`), never estimates.
- The pilot is cost-aware: give a size (S / M / L) before big work, and prefer the quick sure fix plus a written note when they ask for it. They often work 02:00-05:00, inside their Core Sleep block.
