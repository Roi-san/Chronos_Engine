# Start here

For anyone, a person or a new AI session, picking up work on this repository. Ten minutes here saves hours.
Last updated: 2026-11-18 (update this line, and "Where things stand", every work session).

## What Chronos is

Chronos Engine is a local "life engine". You describe your life once: goals, commitments, habits and chores, routines, a day template with your fixed times, and the status dimensions you track (health, energy, focus, ...). Its scheduler, **Kairos**, then plans each day around all of that and around how you feel today.

- Data: YAML files under `user/`, one file per item.
- Ways in: the CLI (`python modules/console.py <command>`), a local dashboard (`utilities/dashboard/server.py`, with Home as the landing page), and a background listener (alarms, reminders, the timer).
- An AI copilot, Nia, runs through ADUC (`Agents Dress Up Committee/`) and supports only the Gemini and Codex CLIs. It has never been tested here, because it sends personal data to an external service.

## Who is who

- **The friend** is Chronos's original author and works upstream. Their newest branch is `alpha_v0.3` (`07a2bf1`, 2026-04-17). Git remotes: `upstream` (theirs) and `origin` (the pilot's fork).
- **The pilot** is the person this work is for. They use Chronos themselves and want a few friends to use it.
- Work happens on **`home-hub-fixes`**, built on `home-hub`, both pushed to `origin`. Nothing is merged upstream; scheduler changes are a prototype for the friend to review.

## The philosophy (do not skip this)

The friend's: life's problem is structure, not motivation. Chronos makes structure visible as nested layers (week, day, routine, subroutine, microroutine, item), and each weekday can be dedicated to one part of life (`docs/philosophy.md`, `docs/guides/what_is_chronos/`).

The pilot's, which decides every behaviour choice:

1. Chronos is a kind, outsourced planner that helps you plan, start and switch tasks. A plan so strict that you do not dare open it has failed.
2. Forgiving by default, strict only by choice. Every rule that could feel strict gets a setting.
3. Keep things visible. Seeing an item and skipping it beats not seeing it; nothing silently disappears.
4. Never punish. Missed things come back with a little more push, never as penalties or double portions.
5. Philosophical choices belong to the pilot. Offer the options with a recommendation, then write the decision down.
6. Usable first. Fix what breaks or lies in the daily loop before building new features.

What that looks like in the code: status scale-down with one step of Grace, lighter versions and "saved for a better day" (`docs/scheduling/status_scale_down_design.md`); "the day starts when you wake up" (`sleep_after_midnight.md`); breathing room only from spare time (`gaps_and_breathing_room.md`); items without a length still get planned (`item_lengths.md`).

## Read in this order

1. This file.
2. `docs/ROADMAP.md`: the agreed strategy, the phases, the open decisions (D1-D4).
3. `docs/ISSUES_AND_NEXT_STEPS.md`: every known issue with a number, next tasks, and what is done (with commits).
4. `docs/WORKLOG.md`: every change in order. Read the last few entries.
5. The design doc of whatever you touch, in `docs/scheduling/`.
6. `docs/reference/item_properties.md`: what Kairos v2 does with each item field (checked against the code).
7. `docs/dev/architecture.md`: the runtime overview.
8. `docs/HOME_HUB_HANDOVER.md`: what the branches changed, written for the friend.

Two old pages, `docs/scheduling/scheduling_algorithm_overview.md` and `scheduling_algorithm_deep_dive.md`, describe the archived v1 scheduler (they carry a banner).

## Where things live

| Path | What |
| --- | --- |
| `commands/*.py` | One file per console command (`run(args, properties)`). `today.py` routes `today` / `today reschedule` to Kairos v2. |
| `modules/console.py` | The CLI: parsing, dispatch, scripts. |
| `modules/item_manager.py` | Item files: create, read, write. |
| `modules/scheduler/kairos_v2.py` | **Kairos v2, the only scheduler that runs** (about 7600 lines; map below). |
| `modules/scheduler/direction.py` | Goal and commitment pressure, periods, "was it done" history. |
| `modules/scheduler/runtime.py` | The day file format and the timer's plan (`build_schedule_plan`). |
| `modules/scheduler/v1.py` | Template helpers Kairos uses, and the schedule-file editors behind `trim`, `cut`, `shift`, `mark` and friends. |
| `modules/scheduler/kairos.py`, `weekly_generator.py`, `verify_kairos.py` | Kairos v1 stubs that only raise. The full v1 is in git history: `git show b1b0bb2:modules/scheduler/kairos.py`. |
| `modules/timer/main.py` | The timer, including Start day. |
| `modules/<type>/main.py` | Per-type behaviour (habit, commitment, task, ...). |
| `utilities/dashboard/server.py` | The dashboard's HTTP server. |
| `utilities/dashboard/home_api.py` | Home's data: turns Kairos's records into sentences (`status_effects`, `length_notes`). |
| `utilities/dashboard/views/`, `widgets/`, `wizards/`, `popups/`, `gadgets/` | Drop-in dashboard components (`views/home/` is Home). |
| `user/` | Data. Shipped defaults are tracked in git; **the pilot's real data lives here too: never test in it.** |
| `tests/` | The suite. `chronos_fixture.py` builds a temporary fake user. |
| `scripts/regression/` | Fake-life plan dumps and probes for before/after comparisons (see its README). |
| `docs/` | Everything above, plus feature pages and references. |

There have been three schedulers: an unreachable pre-Kairos one at the bottom of `commands/today.py`, Kairos v1 (archived), and **Kairos v2**. Only v2 runs.

## Kairos v2 in one page

`KairosV2Scheduler(context).generate_schedule(date)` runs these phases in order (method names are searchable):

| Phase | Decides | Notes on what this branch added |
| --- | --- | --- |
| `gather_information`, `model_reality` | Settings, current status, today's completions, manual injections and adjustments | |
| `model_sleep`, `commit_sleep` | Sleep debt; whether you are inside a sleep block now; the sleep prompt's answer | |
| `select_week_template`, `derive_week_days`, `select_day_template` | Which day template applies | Template choice: weekday, `prioritize:` preferences, closest status, then name |
| `commit_anchor_skeleton` | Anchors (`reschedule: never`) and hard injections | |
| `model_day_budget` | Where the plan ends (the next bedtime) | `_resolve_next_bedtime`, `PLAN_LAST_MINUTE_OF_DAY` |
| `build_candidate_universe` | What is in scope today | Goals/commitments push items in (`direction.py`); every candidate passes through `_normalize_candidate`, where items without a length get one (`_effective_length`) |
| `remove_reality_impossible_candidates` | Drops done/skipped items; scales down to today's status | `_scale_down_for_status` |
| `populate_day_and_windows` and the window phases | Fixed-time slots, windows | `_fill_structure_length`, `_scale_down_fixed_time_nodes` |
| `handle_gaps_buffers_and_recovery`, `build_runtime_helper_windows`, `place_remaining_structure` | Gap filling; helper windows for urgent work | `_runtime_helper_settings` (earliest gap) |
| `run_pressure_relief_pipeline` | Overflow: lighter versions, then trims, then cuts, only where allowed | |
| `fill_quick_wins`, `finalize_conceptual_schedule` | Final blocks | Breathing room in `_apply_breathing_room` |
| `build_timer_handoff`, `persist_decision_log_artifact` | The timer's units; the decision log | `_build_timer_execution_units` |

Scoring: `_urgency_bonus` adds due date, deadline, goal and commitment points; weights come from `user/settings/scheduling_priorities.yml` (0-10, 5 neutral, 0 off).

**Output.** `user/schedules/schedule_YYYY-MM-DD.yml` with `kind: kairos_v2_day_runtime` and a `schedule` map of records: `day_template`, `day_budget`, `candidate_universe`, `assumed_lengths`, `reality_filtered_candidates`, `status_scale_down`, `direction`, `day_population`, `conceptual_schedule`, `breathing_room`, `timer_handoff`, and more. The decision log is `user/logs/kairos_v2_decision_log_latest.md`. Home reads the day file through `home_api.py`; the view only displays.

**Settings Kairos v2 reads.** `scheduling_priorities.yml` (weights), `scheduling_settings.yml` (`default_duration_minutes`, `runtime_helper_windows`), `buffer_settings.yml` (`global_dynamic_buffer`), `status_settings.yml` with each `<dimension>_settings.yml`, `quick_wins_settings.yml`, category and priority settings, `map_of_happiness.yml`. It does not read `scheduling_defaults.yml`, and it ignores several options the Today widget sends (issue 11).

## How to work: the checklist for every change

1. `git fetch`, compare with `origin`, read `git log -5`.
2. Read the tracker entry and the design doc.
3. Philosophical choice? Ask the pilot with options and a recommendation. Technical choice? Decide, and write the reason down.
4. Write the tests first and run them on the unchanged code. Record how many fail.
5. Change the code. One shared helper per idea; comments say why, not what.
6. Run the full suite in a throwaway export. The baseline is in "Where things stand"; any failure is new.
7. Scheduler changes: fake-life dumps before and after (`scripts/regression/`) and an end-to-end run of the real `today reschedule`.
8. Dashboard changes: a headless-browser check (`scripts/regression/README.md`).
9. Docs in the same piece of work: the design doc, the reference docs, the tracker, the roadmap, a `docs/WORKLOG.md` entry, and the handover if the friend should know.
10. Commit the code, then the docs with the code's hash. Push.

## Testing recipes

- **Throwaway export:** `git archive HEAD | tar -x -C <dir>`, then copy your changed files over. Run everything there, never in the repo's `user/`.
- **Suite:** `python -m pytest tests -q -p no:cacheprovider --ignore=tests/test_kairos.py` (`test_kairos.py` tests archived v1). Runs in about 30 seconds.
- **Docs checker:** `python scripts/check_docs_drift.py`.
- **The real command:** `python modules/console.py today reschedule`. Inside a sleep block it asks the sleep question; answer on the command line with `sleep_policy:stay_awake` (or `go_back_to_sleep`). `template:<name>` forces a day template.
- **What Home would show:** `python scripts/regression/e2e_home.py <export>`.
- **Dashboard:** `CHRONOS_DASH_PORT=8799 python utilities/dashboard/server.py` in the export, then the browser script in `scripts/regression/`.

## Gotchas

- `python -I` hides PyYAML on the pilot's machine (it is in user site-packages). Run project code without `-I`.
- After switching branches on Windows, folder casing can stay stale (`Modules` vs `modules`) and break imports.
- A new file missing from `git status`? Check `git check-ignore -v <file>` (the `debug_*` rule used to hide files).
- `new` writes `duration: 0` when no length is given; Kairos then plans the default length.
- The Startup popup covers the dashboard in a headless browser; remove `.alpha-launch-overlay` before clicking.
- Old dumps have LF line endings and new ones CRLF; compare with `diff --strip-trailing-cr`.

## Where things stand

- 2026-11-18: on `home-hub-fixes`, latest commit pushed. Full suite: **380 tests, 378 pass**; the 2 in `tests/test_timer_anchor_wait.py` fail only between 22:30 and midnight (issue 21, a test bug). Any other failure is new.
- Roadmap phase 1, "nothing silently missing": 1a item lengths done (D1), 1b habit tests done. Next: 1c recurring items (D2), built exactly as written in `docs/scheduling/recurrence_design.md` (the pilot gave the go on 2026-11-18); not started.
