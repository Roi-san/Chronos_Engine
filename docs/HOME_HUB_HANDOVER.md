# Home hub branch: what changed and what still needs attention

Branch `home-hub`, built on `origin/alpha_v0.3` (`07a2bf1`). Committed in `f44cd71` and `7768099` and pushed to `origin/home-hub`; not merged into `alpha_v0.3`.
Work continued on `home-hub-fixes` (built on `home-hub`, pushed to `origin/home-hub-fixes`). Its fixes, the open issues and the next tasks are tracked in `docs/ISSUES_AND_NEXT_STEPS.md`; the entries below marked `home-hub-fixes` come from there.
Scheduler details are in `docs/scheduling/builder_templates_prototype.md` and `docs/scheduling/direction_goals_commitments.md`. The Home page is described in `docs/guides/home.md`.

## In one paragraph

The dashboard now opens on a **Home** page: what to do right now, today's plan, a status check-in, quick capture with `#tags`, a setup checklist that opens the existing wizards, and one card per area of life. Nothing was removed; every wizard, builder, widget and view still works. The scheduler (Kairos v2) can now plan a day built in the Day Builder, Routine Builder or Life Setup wizard; before, such a day came out almost empty. Along the way about fifteen bugs were fixed in the console commands, the dashboard and the item store.

## What changed

### New
| File | What it is |
| --- | --- |
| `utilities/dashboard/views/home/` | The Home view. Default landing page; the **⌂ Home** button in the top bar returns to it. |
| `utilities/dashboard/home_api.py` | `GET /api/home/summary`, read-only. Home makes every change through the existing endpoints. |
| `tests/test_kairos_v2_builder_templates.py` | 12 scheduler tests for builder-made days. |
| `docs/guides/home.md`, `docs/scheduling/builder_templates_prototype.md`, this file | Documentation. |

### Scheduler (Kairos v2), as a prototype for review
- Reads the time fields the builders write (`ideal_start_time` / `ideal_end_time`).
- Places timed blocks authored under `children`, not only under `sequence`.
- Understands durations like `15m`, `90 min`, `1h30m`.
- Finds routines whose files use `Name:` rather than `name:`.
- A routine placed as one block no longer has its steps scheduled a second time.
- An item skipped today is not handed back on the next re-plan.
- `sleep_gate.py` was missing `import os` and crashed on builder-made days.
- **Goals and commitments are ranking factors** (`modules/scheduler/direction.py`). Work linked to a goal ranks higher as its date nears; work a commitment counts ranks higher as the period runs out, peaks on the last possible day, and gets extra push after a missed period.
- **Scale-down.** When today's status does not fit an item and a lighter version was authored (`mini_of`), Kairos schedules the lighter one, and it still counts toward the commitment.
- **Where the day ends** (`home-hub-fixes`, 2026-11-18). A bedtime after midnight (e.g. 02:00) used to empty the whole day. Now the plan runs to 23:59, or up to the bedtime when it is past midnight and the bedtime is still ahead. No sleep block plans to 23:59 instead of 16:00. "Go back to sleep" in the sleep prompt plans from wake-up instead of planning no flexible work. `docs/scheduling/sleep_after_midnight.md`.
- **Gaps and breathing room** (`home-hub-fixes`, 2026-11-18). Urgent work takes the earliest gap it fits (helper windows used to need 30+ minutes, so urgent work went after a fixed slot while ordinary work took the gap before it). The `global_dynamic_buffer` in `buffer_settings.yml`, ignored by v2 until now, adds 5 minutes between items and around fixed blocks where there is room. "Light days" (pack or spread) is an open decision. `docs/scheduling/gaps_and_breathing_room.md`.
- **Timer breaks** (`home-hub-fixes`, 2026-11-18). A day-template block with `subtype: break` and a fixed time is run by the timer (`start day`) as a break. Kairos v2 had dropped the subtype, so the break was treated as work to complete (a completion prompt and points). `tests/test_kairos_v2_timer_breaks.py`.
- **Recurring items** (`home-hub-fixes`, 2026-11-19, decision D2, `0d0578a`). `weekly` used to be planned every day and `monthly` / `quarterly` / `yearly` never. Now a once-per-period item is planned from its turn until done: a `day:` the user picks (weekday for weekly, day of the month for monthly), or a day Chronos spreads it to, evenly over the period with the other undated items (so the Chore Setup wizard's chores do not all land on one day). A missed turn comes back daily with a push that grows as the period runs out (new row Recurring Pressure in `scheduling_priorities.yml`; importance on tough days, never urgency); done is done for the period. New items record `created` (via `item_manager.generic_handle_new`), and one added after its turn starts next period. One shared helper for days and periods, `modules/scheduler/periods.py`, now serves commitments (scheduler and tracker) and recurring items; the tracker counts Start-day completions. Worth your review: the spread rule, the 24-point calibration, and `created`. `docs/scheduling/recurrence_design.md`.
- **Items without a length** (`home-hub-fixes`, 2026-11-18, decision D1). A task or habit without a length is planned for `default_duration_minutes` (30, `scheduling_settings.yml`) instead of never; a routine without its own length is one block for the total of its steps (it used to vanish together with its steps). Home tags such blocks **no length**; Brain Dump has a Length field. `docs/scheduling/item_lengths.md`.

### Bugs fixed elsewhere
- `new` ignored the properties you gave it (a 30-minute task was saved with duration 0).
- `set <type> <name> key:value` from the console never set anything.
- `mark "Name":status` from the console always failed.
- `today` (the view) crashed on the new schedule format.
- Tags were saved as text instead of a list; filtering by tag in `list` / `find` / `for` did not work; `find` matched nothing at all.
- New milestones got the literal date `{{end_of_year}}`.
- The dashboard's playlists call recursed forever (an error on every load).
- Opening a widget by name from code did nothing (an undefined variable in `app.js`).
- Cockpit could not load four of its panels (old folder names).
- Canvas reported every save as failed.
- (`home-hub-fixes`) `python modules/console.py today reschedule` crashed at exit (exit 139) after saving the schedule: the "done" chime played on a daemon thread that was still inside pygame when Python shut down.
- (`home-hub-fixes`) The Debug Console's TRICK manifest never reached the repository: `.gitignore`'s `debug_*` matched the `widgets/debug_console/` folder. Now `/debug_*`, root files only, as its comment says.
- (`home-hub-fixes`) TRICK highlight lookup threw a TypeError (`".".join(...)`, Python syntax, in `app.js`).
- (`home-hub-fixes`) `skills list` showed the blank skill template as a skill named "<Skill Name>".
- (`home-hub-fixes`, 2026-11-19) The Chore Setup wizard said "Created N chores" but created none of its built-in chores: it copies `<name> _example` habits, which `alpha_v0.3` does not ship, and the dashboard counts a console command as done whenever it exits normally (`run_console_command`; still open as issue 23). It now creates them from its own list when no example exists (and still copies one when it does). Its custom chores were sent as `{type, name, data: {...}}`, which POST /api/item stored as a text field, so a weekly 20-minute chore became a daily habit with no length; now `{type, name, properties}`. It checks each chore after making it and has a day picker for weekly and monthly chores.

### Settings on this machine only
`user/settings/alpha_gate_settings.yml` turns the alpha gate off, so goals, commitments, projects, rewards and achievements are usable. `alphagate reset` in the console turns it back on.

### Testing
Full suite (excluding `tests/test_kairos.py`, which tests the archived v1 scheduler), on `home-hub`: 205 passed, 2 failed. Both also fail on untouched `alpha_v0.3`, which has a third failure (`test_console_plugins`) that this branch fixes. 32 of the passing tests are new. A realistic fake life was also run through every view, widget and wizard in a headless browser.

On `home-hub-fixes` at `b085852` (2026-11-18): **345 passed, 0 failed**; with the item-length change (D1): **365 passed, 0 failed**; with the habit tests (`65355e2`): 380; with recurring items (D2, 2026-11-19): **486 passed, 0 failed**. All three tests that fail on untouched `alpha_v0.3` are fixed: console plugins on `home-hub`, timer break-as-buffer and the TRICK debug-console registry on `home-hub-fixes`.

## What Kairos actually takes into account

| Input | Used when planning? |
| --- | --- |
| Day and week templates: anchors, windows, timeblocks, routines | Yes |
| Habits, including chores (a chore is a habit with `chore: true`) | Yes, as recurring items. Chores get no special treatment. |
| Tasks | Yes, but only those with a due date or deadline, plus anything in the template |
| Status (energy, health, …) | Yes: picks the best-matching day template; on items, swaps in a lighter version (`mini_of`) when today falls short, keeps short items within one step of grace, urgent ones, and ones whose goal/commitment/priority outweighs the strain, and saves the rest for a better day (since `home-hub-fixes`, 2026-11-17; `docs/scheduling/status_scale_down_design.md`). Fixed slots in the day template follow the same rule at their own time: lighter version in the slot, or the slot is freed. Home lists what was saved under "Saved for a better day" with an **Add back** button, and says why a kept block stays ("tough today"). `place` is ignored (deferred in v2). |
| Priority, category, due date, deadline, tags (in window filters), map of happiness | Yes, for ranking and window filling |
| Completed and skipped blocks today | Yes |
| Goals and milestones | Yes, since this branch: linked work is brought into scope and ranked higher as the date nears. A goal with nothing linked to it changes nothing. |
| Commitments (e.g. "3 workouts a week") | Yes, since this branch: needs a `rule` and `targets`. "Never" commitments are not scheduled. |
| Projects | Only through a goal: a task whose project has a `goal:` is treated as serving that goal. |
| **Appointments, reminders, alarms** | **No.** They ring through the listener, but the scheduler does not plan around them. An appointment has to be added to the day as an anchored timeblock to block that time. |

Appointments are the remaining gap between "what my life contains" and "what Kairos plans around".

## Shaky bits that need attention

Issues found later, and the list of next tasks, are tracked in `docs/ISSUES_AND_NEXT_STEPS.md`; the order of work is in `docs/ROADMAP.md`. Since 2026-11-18 the items below also have tracker numbers (shown in brackets), and the tracker is where their status is kept.

### For the friend, highest impact first
1. **The goal and commitment weights are a first calibration.** They were tuned against one fake life and the shipped settings (`docs/scheduling/direction_goals_commitments.md` has the numbers). They need a few real weeks of use, and they are two rows in `scheduling_priorities.yml` to adjust. Also: nothing fires when a commitment's period ends unmet; appointments still do not block time (#17).
2. **Tasks with no due date are never considered**, even if a window's tag filter matches them (`build_candidate_universe`). `task_defaults.yml` sets a due date of tomorrow, which hides this for tasks made with `new`. (#13)
3. **Zero durations.** `generic_handle_new` writes `duration: 0`, and the Brain Dump wizard has no duration field, so its tasks can never be placed. Home warns and offers "Give them 30 min"; a default or a wizard field would fix it at the source. (#12, fixed 2026-11-18: both, `docs/scheduling/item_lengths.md`)
4. **A missed morning routine is re-queued into the afternoon** as one block. Needs a rule such as "do not re-queue after HH:MM". (#14)
5. **Routines show as one block.** The Timer and Home say "Morning Routine", not the current step. Laying the steps out inside the routine's slot would fix both. (#15)
6. **Field-name decision.** The prototype makes Kairos accept what the builders write. The alternative is to make the builders write `start_time` / `end_time`. Both are reasonable; it should be one or the other.
7. **Day template choice.** With several templates and no status requirements, the first by name wins. (#16)
8. ~~**Three tests already fail upstream:** console plugins, timer break-as-buffer, and the TRICK debug-console registry.~~ All three fixed on these branches (see Testing). The timer one was hiding a real bug: authored break blocks were run as work.

### Not tested
- Nia chat (it sends personal data to an external AI service).
- Goal Planning and Chore Setup wizards were opened and checked for errors, but not walked to the end.
- Alarms, reminders and the background listener.
- Week templates and multi-day planning (`tomorrow`, `this`, `next`).

### Small things noticed
- The "Yesterday Check-in" popup appears on startup even when nothing was scheduled yesterday. (Checked 2026-11-18: by design it shows whenever there is anything to log, once a day until dismissed; see issue 7 in `docs/ISSUES_AND_NEXT_STEPS.md`.)
- `/api/profile/avatar` and `happiness_value_name_assoc.yml` return 404 on a fresh install (harmless).
- `prompt_toolkit`, `pystray`, `pywebview` and `playsound` are in `requirements.txt` but not installed on this PC; `install_dependencies.bat` adds them.

## Using an AI to fill in your life

Nia (in the dashboard) runs through ADUC, which supports only two backends: **Gemini CLI** and **Codex CLI** (`Agents Dress Up Committee/settings/launcher_config.yml`, `cli_backend`). Claude is not one of them, and neither is a local model (Ollama).

You can use Claude without Nia: open **Claude Code** in the Chronos folder and talk to it. The agent guide `docs/agents/agents.md` is written for exactly this. Claude reads it, then creates goals, habits, routines and day templates through the same `modules/console.py` commands the dashboard uses, and the result shows up on Home immediately. That works today, with Sonnet or Opus.

Adding Claude as a third ADUC backend, so it can sit inside the Nia widget, would be a small change in `tools/cli_bridge_watcher.py` next to `run_codex` and `run_gemini`. It was not done.
