# Scenario Planning Architecture

## Purpose

This document defines hypothetical starting conditions without modifying canonical game data.

The first scenario feature allows users to override whether individual buildings are treated as available at the beginning of a plan. Canonical planning remains the default baseline.

## Canonical Data

`BuildingLevel.constructed_on_start` remains the value parsed from game assets.

Scenario planning must never mutate parsed buildings, cities, loaded databases, validation exports, or source assets.

When no scenario is supplied, existing Query Layer Version 1.0 behavior must remain unchanged.

## Terminology

- **Canonical starting state:** Parsed `constructed_on_start` values.
- **Effective starting state:** Canonical state after scenario overrides.
- **Canonical plan:** Plan generated without overrides.
- **Scenario plan:** Plan generated with explicit overrides.

## Public Scenario Contracts

Introduce small immutable public contracts, conceptually:

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

- Canonical `BuildingKey` identifies buildings.
- Duplicate overrides are rejected.
- Ordering is deterministic.
- Empty scenarios are valid.
- Empty scenarios are behaviorally equivalent to canonical planning.
- Localized names are never identifiers.

## Override Semantics

For each building:

1. Use the scenario override when one exists.
2. Otherwise use canonical `constructed_on_start`.

### Available at start: `True`

- Satisfies prerequisites.
- Is excluded from construction actions and costs.
- Stops prerequisite traversal at that building.
- Does not consume a construction day.

### Available at start: `False`

- Must be constructed when required.
- Its prerequisite closure is traversed.
- Its cost and construction day are included.
- It appears in legal build orders.

Any existing building in the selected faction may be overridden. A prebuilt building is treated as a supplied starting condition even when its own prerequisites are unavailable.

Reject unknown, malformed, duplicate, or cross-faction overrides.

## Graph Integration

Effective starting availability should become an explicit graph input.

Preferred direction:

```python
build_dependency_graph(
    city,
    target,
    *,
    starting_buildings=effective_starting_buildings,
)
```

When omitted, graph behavior remains canonical.

The graph remains responsible for prerequisite traversal, satisfied boundary nodes, graph nodes, and dependency edges.

## Planner Integration

The planner should continue consuming a dependency graph and legal order.

```text
PlanningScenario
    ↓
Query Layer validates and resolves effective starting state
    ↓
Dependency Graph
    ↓
Planner
    ↓
BuildPlan
```

The desktop must not reproduce graph or planning rules.

## Query Layer Evolution

Add scenario support compatibly, conceptually:

```python
generate_build_plan(
    faction,
    sid,
    level,
    *,
    starting_date=GameDate(1, 1, 1),
    scenario: PlanningScenario | None = None,
)
```

Apply the same optional scenario to:

- `get_cumulative_cost()`
- `enumerate_build_orders()`

Both canonical and scenario planning must share one authoritative pipeline.

Because `BuildingLevel.constructed_on_start` remains canonical, add a scenario-aware prerequisite-status result, conceptually:

```python
@dataclass(frozen=True, slots=True)
class PrerequisiteStatus:
    building: BuildingLevel
    available_at_start: bool
    overridden: bool
```

The desktop must not infer effective status from the canonical field.

## Cost Consistency

The same immutable scenario object must be passed to every related query.

`BuildPlan.total_cost` remains authoritative. Any separate cumulative-cost query must use identical scenario inputs.

## Desktop State

Desktop state must distinguish:

- canonical target selection;
- active scenario;
- current scenario result.

Scenario changes clear prerequisite statuses, plan steps, costs, completion date, and alternative orders. Target selection may remain.

## Desktop Controls

The UI Engineer owns exact interaction design.

Recommended first control:

```text
Checked   = available at plan start
Unchecked = must be constructed if required
```

Display canonical and effective values clearly:

```text
[✓] Wall   Canonical: available
[ ] Wall   Canonical: available · Overridden
```

Provide:

```text
Reset to Canonical Starting State
```

Resetting removes overrides rather than storing redundant values.

## Result Presentation

Clearly label the planning mode:

```text
Planning mode: Canonical
```

or:

```text
Planning mode: Custom starting state
Overrides: 1
```

Use effective statuses such as:

- `Available at scenario start`
- `Requires construction`
- `Available at scenario start (user override)`

Do not describe an overridden building as canonically constructed at game start.

## Canonical Baseline

An empty scenario must produce exactly the same graph, steps, dates, costs, completion date, legal orders, and statuses as canonical planning.

Canonical mode remains the default and regression baseline.

## Required Regression Scenarios

### Remove a canonical starting prerequisite

Target:

```text
Faction: undead
SID: Build_Tier_6
Level: 1
```

Override:

```text
Build_Wall level 1 → available_at_start=False
```

Expected direction:

- Wall becomes a construction action.
- Required Wall prerequisites are included.
- Action count and completion date increase.
- Wall cost is included.
- Its status becomes `Requires construction`.

Exact results must be derived from canonical data during implementation and encoded in tests.

### Add a noncanonical starting building

Choose a target with a normally unavailable prerequisite.

Expected:

- Overridden building disappears from actions.
- Traversal stops at it.
- Cost and completion time decrease.
- Status indicates scenario-start availability.

### Empty scenario and determinism

Empty scenario equals canonical output. Repeated identical scenario planning returns identical results.

## Alternative Build Orders

Alternative build-order UI remains deferred until scenario-aware planning is certified.

Primary plan and alternatives must use the same scenario, deterministic ordering, and finite result limit.

## Compatibility

Treat this as additive Query Layer evolution, conceptually Version 1.1.

Version 1.0 canonical calls remain supported.

## Validation

Backend validation must cover:

- scenario contract validation;
- effective-state resolution;
- true and false overrides;
- canonical equivalence;
- deterministic scenario plans;
- scenario-aware costs and legal orders;
- invalid and cross-faction overrides.

UI validation must cover toggles, reset, override indicators, stale-result clearing, effective status wording, and canonical preservation.

QA must verify canonical data is unchanged after scenario planning.

## Task Sequence

1. **PM-013 — Scenario Planning Architecture**
2. **BE-010 — Scenario Contracts and Graph Support**
3. **BE-011 — Scenario-Aware Query Layer**
4. **QA — Backend Scenario Certification**
5. **UI-006 — Starting-State Controls**
6. **QA — End-to-End Scenario Certification**
7. **UI — Alternative Legal Build Orders**

## Non-Goals

The first scenario release excludes resource-income assumptions, prebuilt dates, partial payments, save-file import, persistence, comparison, optimization, combat, and random map simulation.

## Success Criteria

Scenario planning succeeds when canonical data remains immutable, empty scenarios preserve canonical output, overrides deterministically change traversal/dates/costs/orders, the Query Layer owns semantics, the desktop owns only interaction and presentation, and canonical and custom modes are visibly distinct.
