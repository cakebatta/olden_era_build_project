# Desktop Scenario Manager

## Architecture

The desktop scenario toolbar delegates to `ScenarioController`. The controller owns a
`ScenarioSession`, calls `LocalScenarioRepository`, and maps immutable
`ScenarioDocument` values into the existing planner and economy presenters.

Analysis remains separate from persistence. Loading a document first populates desktop
state, then explicitly regenerates the Build Plan and Resource Ledger through the public
Query Layer.

## Session state and dirty tracking

`ScenarioSession` tracks the active document, current valid candidate, last valid
candidate, saved snapshot, opaque repository conflict token, source state, repository
membership, raw UI edit state, and the current validation issue.

Dirty-state comparison still follows DE-005 for valid persisted content and excludes
`created_at` and `modified_at`. Raw UI risk is tracked independently. This matters when
visible input cannot construct a valid `ScenarioDocument`: a blank name, malformed
resource value, or invalid recruitment quantity still marks the scenario with `*` and
still triggers unsaved-work protection.

An unmanaged new or detached scenario is always considered at risk even when its current
valid content equals its initial baseline.

## Deferred validation

Every user edit first marks raw UI state as edited. The controller then attempts to build
an immutable candidate document.

When construction succeeds, the candidate becomes the latest valid candidate and is
compared semantically with the saved baseline. Restoring all saved values clears the
dirty indicator.

When construction fails, the last valid candidate is retained, the validation issue is
stored, and raw UI risk remains set. No modal dialog is shown during typing. Validation
becomes user-facing only when Save, Save As, Duplicate, Rename, Delete, or Export requires
a valid document.

## Unsaved-work protection

New, Open, Import, and application close use one Save / Discard / Cancel guard.

The guard activates for:

- valid unsaved changes on managed scenarios;
- invalid visible changes on managed scenarios;
- every unmanaged new scenario;
- detached post-delete content;
- imported or duplicated scenarios with later edits;
- any raw UI difference from the saved baseline.

Discard does not validate abandoned input. Cancel leaves the current UI and session
unchanged. The replacement session is installed only after the requested New, Open, or
Import operation succeeds.

## Invalid Save behavior

Save first requires a valid candidate. If visible input is invalid, no repository method
is called, repository bytes remain unchanged, visible input is preserved, the dirty
indicator remains present, and the stored validation issue is presented to the user.
A pending destructive workflow is cancelled when that Save fails.

## Repository location

The composition root creates `LocalScenarioRepository` beneath the per-user application
data directory:

- Windows: `%LOCALAPPDATA%/OldenEraBuildPlanner`
- macOS: `~/Library/Application Support/OldenEraBuildPlanner`
- Linux: `$XDG_DATA_HOME/OldenEraBuildPlanner` or `~/.local/share/OldenEraBuildPlanner`

The composition root supplies canonical game data explicitly; it does not access private
`PlanningQueryService` fields.

## Commands and conflicts

The toolbar exposes New, Open, Save, Save As, Rename, Duplicate, Delete, Import, and
Export. Save and Delete pass the stored opaque conflict token. Stale saves and deletes
preserve repository bytes and active membership. Save As after conflict creates a new
managed identity.

Import passes an external path directly to the repository. Export uses
`export_scenario_document` so current valid unsaved content can be exported without
changing repository bytes, membership, token, timestamps, or dirty state.

## Document mapping and regeneration

`ScenarioController._apply` is the single document-to-desktop path. `_build` is the
single desktop-to-document path. They cover name, description, notes, faction, target,
starting date, starting-building overrides, starting resources, and recruitment actions.

Loaded, imported, duplicated, and Save-As documents regenerate through the existing
`PlanningQueryService`. Analysis results are not persisted and regeneration does not
change dirty state.

## Validation

From `olden_db` run:

```text
python -m scripts.test_desktop_scenario_session
python -m scripts.test_desktop_scenario_manager
python -m scripts.test_desktop_scenario_workflows
python -m scripts.test_desktop_responsiveness
python -m scripts.test_scenario_serialization
python -m scripts.test_scenario_validation
python -m scripts.test_scenario_repository
python -m scripts.test_query_scenarios
python -m scripts.test_query_resource_ledger
python -m scripts.test_query_income_resource_ledger
python -m scripts.test_resource_ledger
python -m scripts.test_desktop_income_timeline
```
