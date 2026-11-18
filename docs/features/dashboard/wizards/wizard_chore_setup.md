# ChoreSetup Wizard

## Overview
Guided setup for recurring chores and cloned starter chore structures.
Wizards should produce deterministic item/settings outcomes that remain editable through normal CLI and dashboard tools.

## What it does (checked 2026-11-19)
- Lists 26 common chores in five columns (5 daily, 7 weekly, 6 monthly, 4 quarterly, 4 yearly), all ticked, plus **custom chores** (name, description, how often, minutes, day).
- **Weekly and monthly chores have a day picker.** "Any day (Chronos spreads it)" is the default: Kairos then spreads chores without a day evenly over the week or month, so no day gets a wall of chores. A picked day is written as `day:` (`saturday`, or `15` for the 15th; `31` always means the last day). Quarterly and yearly chores are always spread.
- **Create Selected Chores** makes each ticked chore as a habit with `chore: true`, `frequency`, `duration`, `description`, `tags: [chore, <frequency>]`, `created` (today) and `day` when picked. It copies a `<name> _example` habit when one exists; otherwise (as on `alpha_v0.3`, which ships none) it creates the chore from its own list. Existing chores are skipped. Each chore is checked after it is made, and the status line names any that could not be made.
- Before 2026-11-19 the wizard said "Created N chores" but created none of its built-in chores (issue 22), and saved custom chores as daily habits with no length (issue 29). Both fixed; see `docs/scheduling/recurrence_design.md`.
- How the chores are then planned (a chore's turn, coming back daily until done, the push as the period runs out): `docs/scheduling/recurrence_design.md`. The walk-through in a real browser: `scripts/regression/chore_setup_check.js`.

## CLI
- Related command patterns: `new chore/task templates; copy item workflows via CLI equivalents`.
- CLI is the verification and fallback path when wizard UI is unavailable or ambiguous.
- Command syntax reference: `docs/reference/cli_commands.md`.

## Dashboard
- Runtime source: `utilities/dashboard/wizards/chore_setup/`
- Primary intent: guided multi-step workflow with reduced setup friction.
- API endpoints used by this wizard:
  - `/api/item`
  - `/api/item?type=`
  - `/api/item/copy`

## Data and Settings
- Wizard outputs should land in canonical `user/*` item files and/or `user/settings/*.yml`.
- Generated artifacts must remain fully compatible with manual CLI edits after creation.

## Operational Workflows
1. Complete wizard start-to-finish with realistic sample inputs.
2. Confirm created/updated entities in CLI (`view`, `list`, or `settings` commands).
3. Re-open wizard to validate edit/re-entry behavior (if supported).
4. Verify no duplicate/corrupt items were created on repeated runs.

## Validation
1. Open `ChoreSetup` from dashboard wizard registry/menu.
2. Execute one full save/apply path.
3. Verify persisted outputs and expected downstream behavior (today plan, trackers, widgets, etc.).

## Related Docs
- `docs/guides/dashboard.md`
- `docs/reference/dashboard_api.md`
- `docs/guides/settings.md`
- `docs/reference/cli_commands.md`





