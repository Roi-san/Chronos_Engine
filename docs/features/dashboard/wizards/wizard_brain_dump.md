# BrainDump Wizard

## Overview
Rapid capture workflow to turn raw thoughts into structured Chronos items.
Steps: Capture (one task per line), Sort (by horizon), Refine (priority, due date, length in minutes, tags). A task left without a length is planned with the default length (`default_duration_minutes`, 30); see `docs/scheduling/item_lengths.md`.
Wizards should produce deterministic item/settings outcomes that remain editable through normal CLI and dashboard tools.

## CLI
- Related command patterns: `new note <name>; append note <name>; new task <name>`.
- CLI is the verification and fallback path when wizard UI is unavailable or ambiguous.
- Command syntax reference: `docs/reference/cli_commands.md`.

## Dashboard
- Runtime source: `utilities/dashboard/wizards/brain_dump/`
- Primary intent: guided multi-step workflow with reduced setup friction.
- API endpoints used by this wizard:
  - `/api/item`
  - `/api/settings?file=`

## Data and Settings
- Wizard outputs should land in canonical `user/*` item files and/or `user/settings/*.yml`.
- Generated artifacts must remain fully compatible with manual CLI edits after creation.

## Operational Workflows
1. Complete wizard start-to-finish with realistic sample inputs.
2. Confirm created/updated entities in CLI (`view`, `list`, or `settings` commands).
3. Re-open wizard to validate edit/re-entry behavior (if supported).
4. Verify no duplicate/corrupt items were created on repeated runs.

## Validation
1. Open `BrainDump` from dashboard wizard registry/menu.
2. Execute one full save/apply path.
3. Verify persisted outputs and expected downstream behavior (today plan, trackers, widgets, etc.).

## Related Docs
- `docs/guides/dashboard.md`
- `docs/reference/dashboard_api.md`
- `docs/guides/settings.md`
- `docs/reference/cli_commands.md`





