# Scenario Planning Architecture

## Purpose

This document defines hypothetical starting conditions without modifying canonical game data.

`PlanningScenario` is semantic planning input. It is distinct from both canonical parsed state and the broader application-level `PlanningSelection`.

## Canonical Data

`BuildingLevel.constructed_on_start` remains the value parsed from game assets.

Scenario planning must never mutate parsed buildings, cities, loaded databases, validation exports, or source assets.

When no scenario is supplied, canonical Query Layer behavior remains unchanged.

## Terminology

- **Canonical starting state:** Parsed `constructed_on_start` values.
- **Effective starting state:** Canonical state after scenario overrides.
- **Canonical plan:** Plan generated without overrides.
- **Scenario plan:** Plan generated with explicit overrides.
- **Planning selection:** Application-level player intent containing one target, date, and scenario for the initial interactive release.
- **Workspace state:** Transient application orchestration state, including revisions, pending status, accepted results, and failures.

## Public Scenario Contracts

Scenario contracts are immutable and use canonical `BuildingKey` identity.

Conceptually:

```python
@dataclass(frozen=True, slots=True, order=True)
class StartingBuildingOverride:
    building: BuildingKey
    available_at_start: bool


@dataclass(frozen=True, slots=True)
class PlanningScenario:
    starting_building_overrides: tuple[StartingBuildingOverride, ...] = ()
```

Requirements:

- duplicate overrides are rejected;
- ordering is deterministic;
- empty scenarios are valid;
- empty scenarios are equivalent to canonical planning;
- localized names are never identifiers;
- unknown, malformed, duplicate, or cross-faction overrides are rejected.

## Override Semantics

For each building:

1. use the scenario override when present;
2. otherwise use canonical `constructed_on_start`.

When available at start is `True`, the building satisfies prerequisites, is excluded from construction actions and costs, stops prerequisite traversal, and consumes no construction day.

When available at start is `False`, the building must be constructed when required and its prerequisite closure, cost, construction day, and legal-order membership are included.

## Graph and Planner Integration

Effective starting availability is an explicit graph input.

```text
PlanningScenario
    ↓
Query Layer validates and resolves effective starting state
    ↓
Dependency Graph
    ↓
Planner
    ↓
PlannerResult
```

The planner continues to consume a dependency graph and legal order. It remains scenario-independent.

The desktop must not reproduce graph, planning, or effective-state rules.

## Query Layer Integration

Scenario support is additive to planning, cost, order, prerequisite-status, diagnostic, and ledger operations.

Both canonical and scenario planning share one authoritative pipeline.

`BuildPlan.total_cost` remains authoritative. Related queries must receive identical scenario inputs when they describe the same hypothetical state.

## Planning Workspace Integration

Each base entry in the Planning Workspace owns its own immutable `PlanningScenario` as part of its semantic `PlanningSelection`.

For the initial interactive implementation, one selection contains:

```text
faction
one canonical target
starting date
PlanningScenario
```

A scenario edit creates a new selection revision.

If the selection is complete, the application marks it pending and replans automatically through the Query Layer.

The workspace, not the scenario contract, owns:

- revision counters;
- pending, ready, and failed states;
- accepted prior results;
- stale-completion rejection;
- in-flight execution state.

The scenario remains pure semantic input.

## Result Lifecycle

The previous rule that scenario changes simply clear all results is superseded by the Planning Workspace lifecycle.

On a scenario change:

1. create a new immutable planning selection;
2. increment the selection revision;
3. mark the entry pending or incomplete;
4. execute planning when complete;
5. accept only a completion matching the current revision.

The latest accepted result may remain visible during replacement or after failure, but presentation must clearly identify it as retained previous information.

An old result must never be represented as current for the new scenario.

## Desktop Controls

The UI Engineer owns exact interaction design.

Controls may represent effective starting availability with checkboxes, but checkbox state is not the scenario or planning contract.

Canonical and effective values must remain distinguishable, and reset-to-canonical behavior removes redundant overrides rather than storing them.

## Multi-Base Direction

Each base entry owns an independent scenario.

A future workspace may contain up to five base entries without changing scenario semantics or planner behavior.

Workspace-level settings must not be made global merely because an early UI presents only one control.

## Canonical Baseline

An empty scenario must produce the same graph, steps, dates, costs, completion date, legal orders, statuses, diagnostics, and ledger behavior as canonical planning.

Canonical mode remains the default regression baseline.

## Compatibility

Scenario planning remains additive.

Existing canonical calls remain supported.

The Planning Workspace does not replace `PlanningScenario`; it composes it into a broader semantic selection and transient execution lifecycle.

## Validation

Backend validation must cover:

- scenario contract validation;
- effective-state resolution;
- true and false overrides;
- canonical equivalence;
- deterministic scenario plans;
- scenario-aware costs, diagnostics, and legal orders;
- invalid and cross-faction overrides.

Workspace and UI validation must cover:

- scenario edits increment revisions;
- automatic replanning;
- stale-result rejection;
- retained-result labeling;
- reset behavior;
- canonical preservation.

QA performs static certification. The Project Owner performs runtime verification using engineer-supplied commands.

## Non-Goals

Scenario architecture does not define:

- multi-target planning;
- resource-income assumptions beyond approved deterministic models;
- partial payments;
- save-file import;
- optimization;
- combat;
- random map simulation;
- execution scheduling or debounce.
