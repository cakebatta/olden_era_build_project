# BE-012 — Scenario Comparison Collection Foundation

## Status

Implementation complete; Project Owner runtime verification pending.

## Repository Baseline

- Repository: `cakebatta/olden_era_build_project`
- Branch: `main`
- Baseline commit: `4995d97b9a99bad14da2afd192d425151ac58e92`

## Production Deliverables

Added `olden_db/olden_db/scenario_comparison.py` with:

- `WorkspaceId`
- `ComparisonRole`
- immutable member and collection snapshots
- correlated execution request and outcome contracts
- `ScenarioComparisonCollection`
- `ScenarioComparisonExecutionCoordinator`

## Architectural Behavior

The collection owns stable identity, ordered membership, labels, comparison roles,
collection revision, and immutable snapshots.

Each existing `PlanningWorkspace` remains independently responsible for its
semantic selection, revision, execution state, accepted result, retained result,
failure, and diagnostics.

One shared `PlanningQueryService` serves every workspace. Workspace identity and
comparison metadata never enter Query Layer calls.

Duplication copies only the current immutable `PlanningSelection`. It creates a
new workspace identity and lifecycle, and does not copy accepted results,
retained results, failures, diagnostics, result revisions, or source revision
counters.

Execution acceptance is correlated by both `WorkspaceId` and the captured local
`PlanningExecutionRequest`. Removed identities and stale revisions are rejected.

## Validation

From `olden_db`:

```text
python -m scripts.test_scenario_comparison_collection
python -m scripts.test_planning_workspace
python -m scripts.test_planning_summary_support
python -m scripts.test_planner_diagnostic_pipeline
```

Expected new-suite output:

```text
PASS: test_workspace_identity_membership_and_ordering
PASS: test_independent_revisions_pending_and_failures
PASS: test_duplication_copies_semantics_only
PASS: test_identity_and_revision_execution_correlation
PASS: test_removed_identity_and_shared_service
PASS: test_independent_results_determinism_and_retention
PASS: test_immutable_collection_snapshots
PASS: test_single_workspace_compatibility
PASS: 8 scenario comparison collection checks
```

## Constraints Preserved

No planner, graph, scenario, Query Layer, presenter, asynchronous execution, or
background-worker behavior is changed.
