# Desktop Scenario Manager

## Architecture

The desktop scenario toolbar delegates to `ScenarioController`. The controller owns a
`ScenarioSession`, calls `LocalScenarioRepository`, and maps immutable
`ScenarioDocument` values into the existing planner and economy presenters.

Analysis remains separate from persistence. Loading a document first populates desktop
state, then explicitly regenerates the Build Plan and Resource Ledger through the public
Query Layer.

## Session state

`ScenarioSession` tracks the active document, current candidate, saved snapshot, opaque
repository conflict token, source state, and repository membership. Dirty state is a
semantic comparison of persisted user-authored fields and excludes `created_at` and
`modified_at`. An unmanaged scenario is protected from loss even when its content equals
its initial baseline.

## Repository location

The composition root creates `LocalScenarioRepository` beneath the per-user application
data directory:

- Windows: `%LOCALAPPDATA%/OldenEraBuildPlanner`
- macOS: `~/Library/Application Support/OldenEraBuildPlanner`
- Linux: `$XDG_DATA_HOME/OldenEraBuildPlanner` or `~/.local/share/OldenEraBuildPlanner`

Scenarios are never stored in the source tree, working directory, installation directory,
or canonical game-data directory.

## Commands

The toolbar exposes New, Open, Save, Save As, Rename, Duplicate, Delete, Import, and
Export. New/Open/Import/close share one Save/Discard/Cancel guard. Save and Delete pass
the stored opaque conflict token. Save As and Duplicate use persistence creation services
to receive new UUIDs and timestamps. Delete retains the active content as an unsaved
detached copy.

Import passes an external path directly to the repository. Desktop code never reads or
parses JSON. Export uses the persistence-layer `export_scenario_document` service so the
currently displayed validated state can be exported without saving, changing membership,
changing dirty state, or updating timestamps.

## Conflicts

Stale saves and deletes never overwrite or remove stored content. Version 1 offers
Cancel or Save as Copy after a save conflict. Reload remains available through Open.
No merge behavior exists.

## Document mapping

`ScenarioController._apply` is the single document-to-desktop path. `_build` is the
single desktop-to-document path. They cover name, description, notes, faction, target,
starting date, starting-building overrides, starting resources, and recruitment actions.

## Regeneration

Loaded, imported, duplicated, and Save-As documents regenerate through the existing
`PlanningQueryService`. Persisted starting dates are forwarded to both build-plan and
resource-ledger requests. Analysis results are not stored inside `ScenarioDocument` and
analysis regeneration does not affect dirty state.

## Validation

From `olden_db` run:

```text
python -m scripts.test_desktop_scenario_session
python -m scripts.test_desktop_scenario_manager
python -m scripts.test_desktop_scenario_workflows
python -m scripts.test_scenario_serialization
python -m scripts.test_scenario_validation
python -m scripts.test_scenario_repository
python -m scripts.test_query_scenarios
python -m scripts.test_query_resource_ledger
python -m scripts.test_query_income_resource_ledger
python -m scripts.test_resource_ledger
python -m scripts.test_desktop_income_timeline
```

## Manual walkthrough

Launch the desktop and confirm `Untitled Scenario *` appears. Edit metadata, target,
starting buildings, resources, or recruitment and confirm the asterisk remains. Save,
close, reopen through Open, and confirm all controls and regenerated results return.
Rename and save. Duplicate and confirm the copy becomes active with a new managed
identity. Export, import the export, and confirm import becomes active under another
identity. Delete one managed scenario and confirm its content remains as an unsaved copy.
Attempt New/Open/Import/close with unsaved work and exercise Save, Discard, and Cancel.
Use the repository validation script to create a stale token and confirm Save/Delete do
not silently overwrite or remove stored content.
