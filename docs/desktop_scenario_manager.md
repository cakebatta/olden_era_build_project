# Desktop Scenario Manager

## Architecture

The desktop scenario toolbar delegates lifecycle intent to `ScenarioController`. The
controller owns a `ScenarioSession`, calls `LocalScenarioRepository`, and maps immutable
`ScenarioDocument` values into the existing planner and economy presenters.

Analysis remains separate from persistence. Loading a document first populates desktop
state, then explicitly regenerates the Build Plan and Resource Ledger through the public
Query Layer.

UI-015 adds a presentation adapter, `InlineValidationScenarioController`, which exposes
session-owned validation metadata to the view. It does not own validation rules and does
not change persistence, dirty-state, or lifecycle behavior.

## Session state and dirty tracking

`ScenarioSession` tracks the active document, current valid candidate, last valid
candidate, saved snapshot, opaque repository conflict token, source state, repository
membership, raw UI edit state, and the current validation issue.

Dirty-state comparison still follows DE-005 for valid persisted content and excludes
`created_at` and `modified_at`. Raw UI risk is tracked independently. Visible input that
has not yet been reconstructed still marks the scenario with `*` and still triggers
unsaved-work protection.

An unmanaged new or detached scenario is always considered at risk even when its current
valid content equals its initial baseline.

## Commit-only reconstruction and deferred validation

Normal typing does not reconstruct a `ScenarioDocument` and does not run domain
validation. The edit callback records raw UI risk and refreshes presentation state only.
This preserves the edit-first workflow and prevents validation feedback from appearing
while the user is typing.

A candidate document is reconstructed only when a command requires valid scenario
content. These commit operations are Save, Save As, Rename, Duplicate, Delete, and
Export. Pending New, Open, Import, and application-close transitions can also reach the
same commit path when the unsaved-work guard is answered with Save.

When reconstruction succeeds, the candidate becomes the latest valid candidate, its
validation issue is cleared by `ScenarioSession`, and semantic dirty-state comparison is
performed against the saved baseline.

When reconstruction fails, the last valid candidate is retained, the domain exception is
stored in `ScenarioSession.validation_issue`, raw UI risk remains set, and the existing
modal error is shown. After that dialog is dismissed, the adapter exposes the stored
field path and message to the view for inline presentation. A pending transition is
cancelled when its Save attempt fails.

## Inline validation presentation

The view receives a field path and message that were produced by domain reconstruction.
It does not evaluate field values or duplicate domain rules.

For a reported metadata issue, the view:

- decorates the affected field;
- displays one pre-created inline message;
- restores keyboard focus to the first affected field after the dialog closes; and
- keeps the decoration visible until a later successful reconstruction clears the
  session issue.

Repeated failed commit attempts reuse the same field decoration and message widgets.
Successful reconstruction clears all metadata validation presentation automatically.

The Scenario Manager header directly edits only the metadata fields `name`,
`description`, and `notes`. Those are therefore the only fields mapped by this view for
inline validation. Other visible planner and economy inputs are owned and presented by
their respective views; UI-015 does not broaden the Scenario Manager view's
responsibility for them.

## Unsaved-work protection

New, Open, Import, and application close use one Save / Discard / Cancel guard.

The guard activates for:

- valid unsaved changes on managed scenarios;
- invalid or unreconstructed visible changes on managed scenarios;
- every unmanaged new scenario;
- detached post-delete content;
- imported or duplicated scenarios with later edits; and
- any raw UI difference from the saved baseline.

Discard does not reconstruct or validate abandoned input. Cancel leaves the current UI
and session unchanged. The replacement session is installed only after the requested
New, Open, or Import operation succeeds.

## Invalid Save behavior

Save first requires a valid candidate. If reconstruction fails, no repository method is
called, repository bytes remain unchanged, visible input is preserved, the dirty
indicator remains present, and the stored validation issue is presented to the user.
A pending destructive or replacement workflow is cancelled when that Save fails.

## Repository location

The composition root creates `LocalScenarioRepository` beneath the per-user application
data directory:

- Windows: `%LOCALAPPDATA%/OldenEraBuildPlanner`
- macOS: `~/Library/Application Support/OldenEraBuildPlanner`
- Linux: `$XDG_DATA_HOME/OldenEraBuildPlanner` or `~/.local/share/OldenEraBuildPlanner`

The composition root supplies canonical game data explicitly; it does not access private
`PlanningQueryService` fields.

## Commands and conflicts

The toolbar exposes New, Open, Save, and a Scenario menu containing Save As, Rename,
Duplicate, Import, Export, and Delete. Save and Delete pass the stored opaque conflict
token. Stale saves and deletes preserve repository bytes and active membership. Save As
after conflict creates a new managed identity.

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

## Repository hygiene

Python bytecode is not source material and must not be committed. The repository ignore
rules cover both `__pycache__/` directories and `*.py[cod]` files. Certification includes
checking the tracked file list for `*.pyc`, `*.pyo`, and `*.pyd` artifacts.

## Validation

From `olden_db` run:

```text
python -m scripts.test_desktop_inline_validation
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

From the repository root, verify tracked bytecode separately with:

```text
git ls-files "*.pyc" "*.pyo" "*.pyd"
```

The command must produce no output.
