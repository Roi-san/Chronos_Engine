# Home hub branch: what changed and what still needs attention

Branch `home-hub`, built on `origin/alpha_v0.3` (`07a2bf1`). Nothing is committed yet.
Scheduler details are in `docs/scheduling/builder_templates_prototype.md`. The Home page is described in `docs/guides/home.md`.

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

### Settings on this machine only
`user/settings/alpha_gate_settings.yml` turns the alpha gate off, so goals, commitments, projects, rewards and achievements are usable. `alphagate reset` in the console turns it back on.

### Testing
Full suite (excluding `tests/test_kairos.py`, which tests the archived v1 scheduler): 184 passed, 3 failed. The same 3 fail on untouched `alpha_v0.3`. A realistic fake life was also run through every view, widget and wizard in a headless browser.

## What Kairos actually takes into account

| Input | Used when planning? |
| --- | --- |
| Day and week templates: anchors, windows, timeblocks, routines | Yes |
| Habits, including chores (a chore is a habit with `chore: true`) | Yes, as recurring items. Chores get no special treatment. |
| Tasks | Yes, but only those with a due date or deadline, plus anything in the template |
| Status (energy, health, place, …) | Yes: picks the best-matching day template and filters items with `status_requirements` / `place` |
| Priority, category, due date, deadline, tags (in window filters), map of happiness | Yes, for ranking and window filling |
| Completed and skipped blocks today | Yes |
| **Goals and milestones** | **No.** Kairos never reads them. |
| **Commitments** (e.g. "3 workouts a week") | **No.** They are evaluated after the fact by `commitments check`, not used to plan. |
| **Projects** | **No.** A task's `project:` has no effect on planning. |
| **Appointments, reminders, alarms** | **No.** They ring through the listener, but the scheduler does not plan around them. An appointment has to be added to the day as an anchored timeblock to block that time. |

So today the link from "what I'm aiming for" to "what I do today" runs only through tasks, habits and their priority. A goal does not pull its tasks forward, and a commitment that is falling behind does not get its habit scheduled sooner.

## Shaky bits that need attention

### For the friend, highest impact first
1. **Goals, commitments and appointments do not reach the scheduler.** This is the biggest gap against the "load your life once and let Chronos plan it" idea. Suggested start: score boost for tasks linked to an active goal or milestone; boost for habits that a lagging commitment targets; appointments with a date and time become anchors for that day.
2. **Tasks with no due date are never considered**, even if a window's tag filter matches them (`build_candidate_universe`). `task_defaults.yml` sets a due date of tomorrow, which hides this for tasks made with `new`.
3. **Zero durations.** `generic_handle_new` writes `duration: 0`, and the Brain Dump wizard has no duration field, so its tasks can never be placed. Home warns and offers "Give them 30 min"; a default or a wizard field would fix it at the source.
4. **A missed morning routine is re-queued into the afternoon** as one block. Needs a rule such as "do not re-queue after HH:MM".
5. **Routines show as one block.** The Timer and Home say "Morning Routine", not the current step. Laying the steps out inside the routine's slot would fix both.
6. **Field-name decision.** The prototype makes Kairos accept what the builders write. The alternative is to make the builders write `start_time` / `end_time`. Both are reasonable; it should be one or the other.
7. **Day template choice.** With several templates and no status requirements, the first by name wins.
8. **Three tests already fail upstream:** console plugins, timer break-as-buffer, and the TRICK debug-console registry.

### Not tested
- Nia chat (it sends personal data to an external AI service).
- Goal Planning and Chore Setup wizards were opened and checked for errors, but not walked to the end.
- Alarms, reminders and the background listener.
- Week templates and multi-day planning (`tomorrow`, `this`, `next`).

### Small things noticed
- The "Yesterday Check-in" popup appears on startup even when nothing was scheduled yesterday.
- `/api/profile/avatar` and `happiness_value_name_assoc.yml` return 404 on a fresh install (harmless).
- `prompt_toolkit`, `pystray`, `pywebview` and `playsound` are in `requirements.txt` but not installed on this PC; `install_dependencies.bat` adds them.

## Using an AI to fill in your life

Nia (in the dashboard) runs through ADUC, which supports only two backends: **Gemini CLI** and **Codex CLI** (`Agents Dress Up Committee/settings/launcher_config.yml`, `cli_backend`). Claude is not one of them, and neither is a local model (Ollama).

You can use Claude without Nia: open **Claude Code** in the Chronos folder and talk to it. The agent guide `docs/agents/agents.md` is written for exactly this. Claude reads it, then creates goals, habits, routines and day templates through the same `modules/console.py` commands the dashboard uses, and the result shows up on Home immediately. That works today, with Sonnet or Opus.

Adding Claude as a third ADUC backend, so it can sit inside the Nia widget, would be a small change in `tools/cli_bridge_watcher.py` next to `run_codex` and `run_gemini`. It was not done.
