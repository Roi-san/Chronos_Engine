# Regression scripts and probes

Tools for proving a change, used for every scheduler change since 2026-11-17 (see `docs/START_HERE.md`, "How to work"). None of them are pytest tests and none touch the real `user/` folder: each builds fake data on the repository's temporary test fixture (`tests/chronos_fixture.py`) inside an export you point it at.

## The before/after routine

```bash
git archive HEAD | tar -x -C /tmp/before          # unchanged code
git archive HEAD | tar -x -C /tmp/after           # then copy your changed files into it
for f in rich_dump status_week status_matrix fixed_week plan_dump; do
  python scripts/regression/$f.py /tmp/before > before_$f.txt
  python scripts/regression/$f.py /tmp/after  > after_$f.txt
  diff --strip-trailing-cr before_$f.txt after_$f.txt
done
```

Identical dumps mean the change did not move anything in those fake lives. When they differ, every difference must be explained in the design doc of the change.

## Plan dumps (fake lives over a week)

| Script | What it prints |
| --- | --- |
| `rich_dump.py <export>` | A realistic fake life (sleep, meals, a morning routine, admin and focus windows, habits, tasks, a goal, a commitment) planned for seven days. |
| `status_week.py <export>` | A week where today's status changes every day (good, low, sick, exhausted, ...) with items that need certain status: what is swapped, kept or saved. |
| `status_matrix.py <export>` | One line per status scenario (needs energy high on a sick day, and so on): what Kairos plans. |
| `fixed_week.py <export>` | A week with fixed-time slots that need status (a gym slot, deep work). |
| `plan_dump.py <export>` | The base fixture day, plain. |
| `with_breathing.py <export> <script.py>` | Runs one of the dumps above with breathing room switched on (5/5, the shipped values). |
| `chores_month.py <export>` | Four weeks with all 26 Chore Setup chores (set up on Monday 16 November 2026); a fake user does what is planned, with a few chores skipped on purpose. Per day: the once-per-period chores planned and their state; then a summary (most on one day, which weeks each weekly chore was done). Added with recurring items (D2, 2026-11-19). |
| `compare_days.py <before.txt> <after.txt>` | Compares two dumps day by day: same items? which times moved? any overlaps? |

## Probes (measure one behaviour)

| Script | Measures | Used for |
| --- | --- | --- |
| `sleep_probe.py <export> [--json]` | Where the day ends for different sleep anchors and clock times | `docs/scheduling/sleep_after_midnight.md` |
| `midnight_probe.py <export>` | What breaks downstream when the day ends at 24:00 or later | same |
| `gap_probe.py <export> [--json]` | Where work goes around a fixed slot, and how tightly | `docs/scheduling/gaps_and_breathing_room.md` |
| `break_probe.py <export>` | Whether an authored break block reaches the timer as a break | issue 6 (`91dc4b9`) |
| `routine_probe.py <export>` | How routines with and without their own length are placed | `docs/scheduling/item_lengths.md` |

## What Home would show

`python scripts/regression/e2e_home.py <export>` prints `home_api._today()` for the export: today's blocks as Home lists them. Use it after a real `python modules/console.py today reschedule` inside the export.

## In a real browser

`brain_dump_check.js` drives the dashboard in headless Chrome: Home's **no length** tag, then the Brain Dump wizard with a Length field. Copy its pattern for other dashboard checks.

`chore_setup_check.js` walks the Chore Setup wizard to the end (six built-in chores and one custom weekly chore, days picked where offered) and prints what the wizard says; `python scripts/regression/chore_files.py <export>` then lists what it really wrote (`frequency`, `day`, `duration`, `created`, and any nested `data` field). Always compare the two: the dashboard reports a console command as done whenever it exits normally (issue 23).

```bash
npm install playwright-core@1.48.2            # in any scratch folder
cd <export> && CHRONOS_DASH_PORT=8799 python utilities/dashboard/server.py &
NODE_PATH=<scratch>/node_modules node scripts/regression/brain_dump_check.js http://127.0.0.1:8799 <screenshot dir>
```

Notes: it uses the installed Chrome (`channel: 'chrome'`); it opens `/dashboard.html`, clicks the splash's Enter, and removes the Startup popup (`.alpha-launch-overlay`), which otherwise covers everything; a wizard is opened with `import('/wizards/<name>/index.js')` and `launch(...)`. Stop the server afterwards (on Windows: `Get-NetTCPConnection -LocalPort 8799` then `Stop-Process`).
