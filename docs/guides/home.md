# Home View

Home is the dashboard's landing page. It opens by default when no other view is saved, and the **Home** button at the left of the top bar returns to it from anywhere.

It answers four questions on one screen and hands off to the existing wizards, builders and widgets for everything else.

## What is on the page

| Section | What it does |
| --- | --- |
| **Right now** | Shows the block to do now (or the next one), with time left, and why it is there: the commitment it counts toward, the goal it serves, or that it is a lighter version for today. `Done` and `Skip` call `mark "<block>":completed|skipped`. `Start timer` runs the day through the Timer. `Re-plan from now` runs `today reschedule`. With no day template it points to the Life Setup wizard; with no schedule it offers `Plan my day`. |
| **How are you right now?** | One row of choices per status dimension from `status_settings.yml` (Health, Place and Energy first; the rest behind "Show more"). Picking one calls `/api/status/update`. `Sick day` sets health to poor and energy to low. After a change, `Re-plan my day with this` reschedules. |
| **Get it out of your head** | Quick capture of a task, habit, goal, commitment, project or note. Tasks and habits always get a duration, because the scheduler cannot place an item without one. `#word` in the text becomes a tag: `Call the bank #admin #quick`. Extra fields appear per kind: a task or habit can be linked to a goal or marked as the lighter version of another item; a goal takes a target date and priority; a commitment takes "how often, per day/week/month, of which habit or task". |
| **Today** | The generated schedule as a checklist: done, skipped, not marked, fixed. Named windows show as headings above their contents. Blocks finished or skipped earlier stay listed after a re-plan. A block kept although today's status falls short of it is tagged **tough today**; the tooltip (and Right now) says why, for example "Kept although energy is exhausted (needs high or medium): its deadline is today." A block planned with the default length because it has none is tagged **no length** ("No length set, so Chronos planned 30 min. Set its real length in Manage."); a routine planned from its steps says "Planned for 25 min, the total of its steps." (`docs/scheduling/item_lengths.md`) |
| **Saved for a better day** | Shown only when today's status left something out: each item with what today falls short on ("Today energy is exhausted (needs high).") and, for a fixed slot, its time. **Add back** runs `today inject "<name>" type:<type>` and re-plans: the item goes where it fits, a fixed slot gets its own time back, and status never removes it again today. How Kairos decides: `docs/scheduling/status_scale_down_design.md`. |
| **Set up once** | The path from an empty install to a planned day. Each step is ticked from real data (a day template exists, tasks exist, status is set, today has blocks) and opens the wizard or builder that completes it. |
| **Your life in Chronos** | One card per area: Goals, Commitments, Habits, Routines, Days & weeks, Tasks, Projects, Fixed times. Each shows a count, the first items (with their tags), and buttons into the matching wizard, builder or widget. The Tasks card says when open tasks have no length: Chronos plans them with the default length (`default_duration_minutes`, 30) until you set one, and offers to give them 30 minutes. |

## Alpha gate

Home only offers surfaces the active release profile allows. Under `alpha_v0_3` the engine refuses to create goals, commitments and projects, so those cards say so and offer **Turn on**. That button (and "Show unfinished features too" in the footer) writes `show_hidden_items: true` and `disable_hidden_features: false` to `user/settings/alpha_gate_settings.yml` and reloads. It turns on every hidden feature, not one. Reverse it with `alphagate reset` in the console.

## How it is built

- `utilities/dashboard/views/home/index.js` is a normal auto-discovered view.
- `utilities/dashboard/home_api.py` serves `GET /api/home/summary`: profile, status dimensions and current values, today's blocks with completion states, every life item grouped by type, and the alpha gate snapshot. It only reads.
- `today.status_effects` in that summary is `status_effects()` in `home_api.py`: Kairos's `schedule.status_scale_down` record turned into sentences (`saved`: name, type, fixed slot, text; `kept`: name -> sentence). Saved items that are on the plan anyway or already done today are left out. Tested in `tests/test_home_api_status_effects.py`, including against real Kairos runs.
- Every change goes through existing endpoints: `/api/item`, `/api/status/update`, `/api/cli` (through `window.ChronosRunCliCommand`, so the sleep-conflict prompt still appears).
- Home refreshes when a wizard overlay closes, when the window regains focus, and once a minute.
