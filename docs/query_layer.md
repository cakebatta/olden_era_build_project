# Query Layer Design Specification

## Purpose

The Query Layer is the stable public interface to the backend. It answers planning and analysis questions by coordinating existing backend components while hiding implementation details.

## Responsibilities

The Query Layer may coordinate database, graph, planner, scenario, comparison, decision-summary, recruitment-stock, resource-ledger, diagnostic, and localization modules; validate requests; return deterministic domain objects; and expose canonical discovery information.

It must not:

- parse assets directly;
- duplicate backend algorithms;
- expose connected backend state;
- contain presentation logic;
- own Planning Workspace lifecycle;
- own debounce, scheduling, or stale-result policy.

## Initialization

```python
from olden_db.query import PlanningQueryService

queries = PlanningQueryService.from_default_game_data()
```

Explicit construction remains available for tests and callers that already hold loaded game data.

The supplied backend data is private service state. Application clients must use only documented Query Layer operations.

## Discovery Interface

Discovery methods return immutable tuples of canonical identifiers.

- `list_factions() -> tuple[str, ...]`
- `list_buildings(faction) -> tuple[str, ...]`
- `list_building_levels(faction, sid) -> tuple[int, ...]`

Localized text is not identity.

## Planning Interface

Supported planning operations include:

- `get_building(...) -> BuildingLevel`
- `get_prerequisites(...) -> tuple[BuildingLevel, ...]`
- `get_prerequisite_statuses(..., scenario=None) -> tuple[PrerequisiteStatus, ...]`
- `generate_build_plan(..., scenario=None) -> BuildPlan`
- `generate_planner_result(..., scenario=None) -> PlannerResult`
- `get_cumulative_cost(..., scenario=None) -> ResourceCost`
- `enumerate_build_orders(..., scenario=None) -> tuple[tuple[BuildingKey, ...], ...]`
- `compare_plans(...) -> PlanComparison`
- `generate_decision_summary(...) -> DecisionSummary`
- `generate_resource_ledger(...) -> ResourceLedger`

`generate_build_plan(...)` remains supported for compatibility.

`generate_planner_result(...)` is the preferred planning entry point for application workflows that need the canonical planning result and diagnostics through one deterministic pipeline.

When `scenario` is omitted or `None`, planning behavior remains equivalent to canonical planning.

## Planning Workspace Relationship

The Planning Workspace is an application orchestration concept defined in `docs/planning_workspace_architecture.md`.

It is not Query Layer state.

The workspace may invoke Query Layer planning operations whenever an immutable planning selection changes. The Query Layer receives ordinary canonical inputs and returns deterministic results or documented failures.

The Query Layer does not receive:

- selection revision counters;
- widget state;
- debounce configuration;
- base-view layout;
- pending-state metadata;
- stale-result policy.

Continuous replanning, execution timing, and completion acceptance remain application concerns.

For the initial interactive implementation, each workspace selection maps to one existing single-target planning request.

A future multi-target operation or combined multi-base aggregation operation must be additive and receive separate architectural approval.

## Scenario-Aware Planning

`PlanningScenario` is immutable and contains deterministic starting-building overrides identified by canonical `BuildingKey` values.

The Query Layer resolves the effective immutable starting-building set and passes only that set to dependency-graph construction. The planner remains scenario-independent.

An empty `PlanningScenario()` is behaviorally equivalent to canonical planning.

Related plan, cost, order, status, and ledger requests must receive the same immutable scenario to describe the same hypothetical state.

Clients must use scenario-aware Query Layer results rather than infer effective state from canonical building fields.

## Plan Comparison and Decision Summaries

`compare_plans()` generates each side independently through the authoritative planning pipeline and delegates comparison calculations to the comparison module.

`generate_decision_summary()` delegates planning and comparison, then returns structured facts. Recommendation and presentation remain client responsibilities.

## Resource Ledgers

`generate_resource_ledger()` is the public entry point for income-aware construction and recruitment accounting.

The Query Layer resolves one effective starting state and reuses it throughout plan, income, stock, and ledger generation.

The automatic income model includes certified deterministic town-building income and excludes stochastic or user-unmodeled map income.

## Public Contract

Application clients may import supported Query Layer interfaces from `olden_db.query` and documented stable domain contracts from their defining modules.

The Query Layer is the supported application-facing backend entry point.

Internal parser, database, graph, path, and planner-algorithm implementation details remain private to the backend.

## Behavioral Guarantees

- Canonical SIDs and `BuildingKey` values are authoritative identifiers.
- Query operations are deterministic for identical game data and inputs.
- Discovery results are immutable and deterministically ordered.
- Invalid requests raise documented Query Layer exceptions rather than leaking lower-level lookup failures.
- Canonical initialization is available through `PlanningQueryService.from_default_game_data()`.
- Existing `generate_build_plan(...)` callers remain compatible.
- Empty scenarios preserve canonical output.
- Query Layer behavior is independent of UI event frequency and execution scheduling.

## Compatibility Policy

Documented Query Layer methods, exceptions, stable domain contracts, and behavioral guarantees are public API.

Changes to those contracts require explicit architectural review.

Internal implementation may evolve provided the documented public behavior remains satisfied.

## Validation

Validation must cover:

- canonical planning;
- initialization and discovery;
- scenario equivalence and overrides;
- `generate_planner_result(...)`;
- diagnostics;
- comparisons and decision summaries;
- resource ledgers;
- deterministic repeated calls;
- compatibility of `generate_build_plan(...)`;
- absence of workspace or UI lifecycle state in Query Layer contracts.

Use repository-provided test modules with:

```text
python -m scripts...
```
