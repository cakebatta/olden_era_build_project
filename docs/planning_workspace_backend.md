# Planning Workspace Backend Foundation

## Status

Implemented by BE-010 against ARCH-019.

## Production modules

- `olden_db/planning_workspace.py`
- `olden_db/planning_execution.py`

The implementation is an application orchestration layer above
`PlanningQueryService`. It does not modify planner, graph, diagnostic, scenario,
or existing Query Layer behavior.

## Contracts

`PlanningSelection` is immutable and contains exactly one canonical target:

```text
faction
target BuildingKey
starting date
PlanningScenario
```

`PlanningWorkspace` currently creates one entry identified by `base-1`. The
workspace stores entries as an ordered tuple with stable `BasePlanId` identity
so later base-count expansion does not require planner redesign.

Each semantic selection replacement increments `selection_revision`. Equivalent
replacement is a no-op.

An execution captures an immutable `PlanningExecutionRequest` containing the
base id, selection snapshot, and revision. Results and failures are accepted
only when both revision and selection still match the active entry.

A previous accepted result may remain stored while a newer selection is pending
or failed. `result_is_current` and `retains_previous_result` prevent that result
from being represented as current.

## Execution

`PlanningExecutionCoordinator` performs one synchronous call to
`PlanningQueryService.generate_planner_result`. It maps the selection to the
existing Query Layer arguments and records either the returned `PlannerResult`
or an immutable application failure projection.

It does not implement:

- asynchronous work;
- debounce;
- cancellation inside the planner;
- multi-target planning;
- multi-base behavior;
- UI events or widget state;
- presenter behavior.

## Validation

From the repository's `olden_db` directory:

```text
python -m scripts.test_planning_workspace
python -m scripts.test_planner_diagnostic_pipeline
```

Then run the complete existing repository certification suite.
