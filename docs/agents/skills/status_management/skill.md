# Status Management

## Purpose
Maintain accurate user status context (energy/focus/mood/stress/etc.) and apply it before scheduling decisions.

## When To Use
- User asks to update status signals.
- User says schedule should reflect current state.
- Agent needs status-aware template/priority matching before rescheduling.

## Workflow
1. Read current status.
2. Update only the needed dimensions.
3. Ensure status dimensions and values are defined in settings.
4. Re-run scheduling preview or `today reschedule`.
5. Explain what changed due to status shift.

## Status Settings Files
- `user/settings/status_settings.yml`
  - Canonical status registry used by scheduling and template matching.
- Per-dimension settings files (examples):
  - `user/settings/health_settings.yml`
  - `user/settings/energy_settings.yml`
  - `user/settings/focus_settings.yml`
  - `user/settings/emotion_settings.yml`
  - `user/settings/mind_state_settings.yml`
  - `user/settings/vibe_settings.yml`

Keep per-dimension files aligned with the dimensions defined in `status_settings.yml`.

## Command Patterns
- `status`
- `status energy:low focus:medium mood:flat stress:high`
- `today reschedule`
- `tomorrow`
- `this friday`

## Tagging Items With `status_requirements`
On an item, `status_requirements` says what the item **needs** (the worst state it can still be done in). Being better than needed is never a mismatch. When today falls short, Kairos swaps in the item's lighter version (`mini_of`), keeps it within one step of grace, keeps it when it is urgent or its goal/commitment/priority outweighs the strain, and otherwise saves it for a better day. On a day template, `status_requirements` picks the closest-matching template.

When the pilot asks why something is missing on a low day, read `schedule.status_scale_down` in today's schedule file (`saved` lists each item with the short dimensions, strain and importance). To put it back: `today inject "<name>" type:<type>`; items added by hand are never removed by status. Strictness can be tuned per dimension (`Grace` in `status_settings.yml`) or per item (`status_grace`). Full rules: `docs/scheduling/status_scale_down_design.md`.

Example:
```yaml
name: Deep Work Lite
type: task
duration: 45m
status_requirements:
  energy: low
  focus: medium
```

Variant example:
```yaml
name: Study Block
type: task
duration: 60m
variants:
  - name: low-energy-version
    status_requirements:
      energy: low
    duration: 30m
```

Note: `variants` and legacy top-level status keys (e.g. `energy: low` directly on an item) are not read by Kairos v2. Use `status_requirements`, and a separate lighter item with `mini_of` instead of `variants`.

## Guardrails
- Set status before major schedule rebuilds.
- Avoid overwriting unrelated status fields unless requested.
- If status is uncertain, ask for a quick confirmation before large planning changes.

## References
- `docs/guides/settings.md`
- `docs/reference/cli_commands.md`
- `docs/reference/item_properties.md`
- `docs/scheduling/scheduling_algorithm_overview.md`

