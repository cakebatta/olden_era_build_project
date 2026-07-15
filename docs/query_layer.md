# Query Layer Design Specification

## Purpose

The Query Layer is the stable public interface to the backend. It answers
planning questions by coordinating existing backend components while hiding
implementation details.

## Responsibilities

The Query Layer may coordinate existing database, graph, planner, scenario,
comparison, decision-summary, and localization modules, validate requests,
return deterministic domain objects, and expose canonical discovery
information. It must not parse assets, duplicate algorithms, expose connected
backend state, or contain presentation logic.

## Initialization

```python
from olden_db.query import PlanningQueryService

queries = PlanningQueryService.from_default_game_data()
```

Explicit construction remains available for tests and callers that already
hold a `LoadedGameData` instance:

```python
queries = PlanningQueryService(loaded_data)
```

The supplied backend data is private service state. Application clients must
use only the documented Query Layer operations.

## Discovery Interface

Discovery methods return immutable tuples of canonical identifiers. They do not
return localized text or expose backend collections.

- `list_factions() -> tuple[str, ...]`
- `list_buildings(faction) -> tuple[str, ...]`
- `list_building_levels(faction, sid) -> tuple[int, ...]`

Factions and building SIDs are returned in lexical order. Building levels are
returned in ascending numeric order. Unknown factions raise
`UnknownFactionError`; unknown SIDs raise `UnknownBuildingError`.

## Planning Interface

- `get_building(...) -> BuildingLevel`
- `get_prerequisites(...) -> tuple[BuildingLevel, ...]`
- `get_prerequisite_statuses(..., scenario=None) -> tuple[PrerequisiteStatus, ...]`
- `generate_build_plan(..., scenario=None) -> BuildPlan`
- `get_cumulative_cost(..., scenario=None) -> ResourceCost`
- `enumerate_build_orders(..., scenario=None) -> tuple[tuple[BuildingKey, ...], ...]`
- `compare_plans(...) -> PlanComparison`
- `generate_decision_summary(...) -> DecisionSummary`

When `scenario` is omitted or `None`, planning behavior remains identical to the
Version 1.0 canonical behavior.

## Scenario-Aware Planning

Scenario contracts are imported from `olden_db.scenario`:

```python
from olden_db.scenario import (
    PlanningScenario,
    PrerequisiteStatus,
    StartingBuildingOverride,
)
```

`PlanningScenario` is immutable and contains deterministic starting-building
overrides identified by canonical `BuildingKey` values. The Query Layer
resolves an effective immutable starting-building set and passes only that set
to dependency-graph construction. The planner remains scenario-independent.

An empty `PlanningScenario()` is behaviorally equivalent to canonical planning.
Scenario-aware plan, cost, and build-order queries must receive the same
scenario object to describe the same hypothetical starting state.

`get_prerequisite_statuses()` returns one immutable `PrerequisiteStatus` for
each direct prerequisite, in deterministic SID and level order. Each status
contains:

- `building`: the canonical `BuildingLevel`;
- `available_at_start`: effective scenario availability;
- `overridden`: whether effective availability differs from the canonical
  `constructed_on_start` value.

Clients must use this result rather than interpreting
`BuildingLevel.constructed_on_start` as scenario state.

## Plan Comparison

`compare_plans()` is the public Query Layer entry point for pairwise plan
comparison. It accepts explicit left and right targets, independent optional
scenarios, and one shared starting date.

The Query Layer generates each `BuildPlan` independently through the existing
planning pipeline and delegates all comparison calculations to
`compare_build_plans()` in `olden_db.comparison`. It does not duplicate action,
date, resource, or membership-difference logic.

The returned immutable `PlanComparison` follows right-minus-left semantics.
Positive deltas mean the right plan has more actions, finishes later, or costs
more. Independent scenarios support canonical-to-canonical,
canonical-to-scenario, and scenario-to-scenario comparisons.

## Decision Summaries

`generate_decision_summary()` mirrors `compare_plans()` and supports the same
explicit left and right targets, independent scenarios, and shared starting
date.

The Query Layer first delegates plan generation and comparison to
`compare_plans()`. It then passes the resulting `PlanComparison` directly to
`summarize_plan_comparison()` in `olden_db.decision_summary`.

The Query Layer does not duplicate comparison calculations or construct
decision observations. The returned immutable `DecisionSummary` contains
structured facts only; formatting, recommendation, preference, ranking, and
presentation remain client responsibilities.

## Version 1.0 Public Contract

### Public Modules

Application clients may import the following supported Query Layer interfaces
from `olden_db.query`:

```python
from olden_db.query import (
    PlanningQueryService,
    QueryError,
    UnknownFactionError,
    UnknownBuildingError,
)
```

`olden_db.query` is the supported application-facing backend entry point for
Version 1.0.

### Stable Public Domain Contracts

The Query Layer intentionally returns existing domain objects rather than
introducing wrapper types or data-transfer objects.

The following domain types are stable parts of the Version 1.0 public
contract:

- `BuildingKey`
- `BuildingLevel`
- `ResourceCost`
- `GameDate`
- `BuildPlan`
- `BuildStep`

Application clients may import these types from their existing defining
modules:

```python
from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan, BuildStep, GameDate
```

These objects may be inspected through their documented fields and properties
when returned by Query Layer operations.

### Internal Backend Modules

The following modules are backend implementation details and are not part of
the Version 1.0 public API:

- `olden_db.parser`
- `olden_db.unit_parser`
- `olden_db.database`
- `olden_db.graph`
- `olden_db.localization`
- `olden_db.paths`

Application clients must not import these modules directly. Their internal
structure and implementation may change without constituting a public API
change, provided the documented Query Layer contract continues to be
satisfied.

### Behavioral Guarantees

Version 1.0 guarantees the following behavior:

- Canonical SIDs are the authoritative identifiers.
- Query operations are deterministic for identical game data and inputs.
- `list_factions()` returns faction IDs in lexical order.
- `list_buildings(faction)` returns unique building SIDs in lexical order.
- `list_building_levels(faction, sid)` returns levels in ascending numeric
  order.
- Discovery methods return immutable tuples.
- Invalid Query Layer requests raise documented Query Layer exceptions rather
  than exposing lower-level backend lookup errors.
- Canonical application initialization is available through
  `PlanningQueryService.from_default_game_data()`.

Localization remains a presentation concern and does not replace canonical
identifiers.

### Compatibility Policy

The following are part of the Version 1.0 public API:

- documented `PlanningQueryService` methods;
- documented Query Layer exceptions;
- documented stable domain contracts;
- documented behavioral guarantees.

Changes to any of these constitute public API changes and should receive
explicit architectural review before implementation.

Internal implementation details may evolve without review as public API
changes, provided the documented Version 1.0 contract remains intact.

## Validation

From the outer `olden_db/` directory:

```bash
python -m scripts.test_query
python -m scripts.test_query_initialization
python -m scripts.test_query_discovery
python -m scripts.test_query_scenarios
python -m scripts.test_query_comparison
python -m scripts.test_query_decision_summary
```
