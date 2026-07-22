# Query Layer Design Specification

## Planning Summary Support

`PlanningQueryService.generate_planner_result(...)` returns the authoritative
accepted planning result. In addition to the existing `plan` and `diagnostics`
contracts, `PlannerResult` exposes:

```text
daily_construction_schedule: tuple[DailyConstructionCost, ...]
```

Each immutable entry contains the construction date, canonical `BuildingKey`,
and individual `ResourceCost` for one accepted plan step. The projection is
created from the accepted plan during normal result construction. It does not
perform another graph traversal or planner execution and therefore shares the
same result lifecycle.

The Query Layer also exposes:

```text
get_building_display_text(building: BuildingKey) -> str
```

This operation resolves presentation text from canonical building identity.
Desktop clients must use this operation rather than importing localization
catalogs, localization parsers, or repository paths.

Existing `generate_build_plan(...)`, `generate_planner_result(...)`, and
`PlanningQueryService(loaded_data)` callers remain compatible.

## Purpose

The Query Layer is the stable public interface to the backend. It answers planning and analysis questions by coordinating existing backend components while hiding implementation details.

## Responsibilities

The Query Layer may coordinate database, graph, planner, scenario, comparison, decision-summary, recruitment-stock, resource-ledger, diagnostic, and planner-localization modules; validate requests; return deterministic domain objects; and expose canonical discovery information.

It must not:

- parse assets directly;
- duplicate backend algorithms;
- expose connected backend state;
- expose localization storage or source policy;
- contain presentation layout logic;
- own Planning Workspace lifecycle;
- own debounce, scheduling, or stale-result policy.

## Initialization

```python
from olden_db.query import PlanningQueryService

queries = PlanningQueryService.from_default_game_data()
```

Canonical initialization loads game data, constructs the immutable
`PlannerLocalizationCatalog` for the configured language, and publishes the
ready service.

Explicit construction remains available for tests and callers that already hold loaded game data.

The supplied backend data and planner-localization catalog are private service state. Application clients must use only documented Query Layer operations.

## Discovery Interface

Discovery methods return immutable tuples of canonical identifiers.

- `list_factions() -> tuple[str, ...]`
- `list_buildings(faction) -> tuple[str, ...]`
- `list_building_levels(faction, sid) -> tuple[int, ...]`

Localized text is not identity.

## Planner Display-Name Interface

ARCH-021 defines the Planner Localization Catalog as the authoritative source of
planner-facing names.

Required public operations are:

```text
get_faction_display_text(faction_sid: str) -> str
get_building_display_text(building: BuildingKey) -> str
get_unit_display_text(faction_sid: str, unit_sid: str) -> str
get_upgrade_display_text(faction_sid: str, upgrade_sid: str) -> str
```

When canonical planner milestones are available, the Query Layer may add:

```text
get_milestone_display_text(milestone_id: str) -> str
```

Every operation:

- accepts canonical identity;
- validates that the canonical entity exists;
- returns one non-empty display-ready string;
- delegates lookup and fallback to the immutable Planner Localization Catalog;
- does not expose localization keys, files, maps, or source precedence.

The mandatory fallback order is:

```text
localized planner name
canonical game-data display name, when available
canonical identifier
```

Known canonical entities with missing localized text use fallback. Invalid
canonical identities raise documented Query Layer errors.

The Query Layer does not change canonical discovery operations to return
localized identity objects.

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
- `compare_accepted_build_plans(...) -> BuildPlanComparisonOutcome`
- `generate_decision_summary(...) -> DecisionSummary`
- `generate_resource_ledger(...) -> ResourceLedger`

`generate_build_plan(...)` remains supported for compatibility.

`generate_planner_result(...)` is the preferred planning entry point for application workflows that need the canonical planning result and diagnostics through one deterministic pipeline.

When `scenario` is omitted or `None`, planning behavior remains equivalent to canonical planning.

Localization configuration must not alter any planning result.

## Planning Workspace Relationship

The Planning Workspace is an application orchestration concept defined in `docs/planning_workspace_architecture.md`.

It is not Query Layer state.

The workspace may invoke Query Layer planning operations whenever an immutable planning selection changes. The Query Layer receives ordinary canonical inputs and returns deterministic results or documented failures.

The Query Layer does not receive:

- selection revision counters;
- widget state;
- debounce configuration;
- workspace layout;
- pending-state metadata;
- stale-result policy.

Continuous replanning, execution timing, and completion acceptance remain application concerns.

Each workspace selection maps to one existing single-target planning request.

A future multi-target operation or combined multi-base aggregation operation must be additive and receive separate architectural approval.

## Scenario Comparison Relationship

Scenario comparison is application collection state.

`compare_accepted_build_plans(...)` compares current accepted planner inputs
without regenerating plans.

The Query Layer does not receive workspace labels, widget identities, or
collection presentation state beyond the immutable accepted inputs required by
the comparison contract.

## Scenario-Aware Planning

`PlanningScenario` is immutable and contains deterministic starting-building overrides identified by canonical `BuildingKey` values.

The Query Layer resolves the effective immutable starting-building set and passes only that set to dependency-graph construction. The planner remains scenario-independent.

An empty `PlanningScenario()` is behaviorally equivalent to canonical planning.

Related plan, cost, order, status, and ledger requests must receive the same immutable scenario to describe the same hypothetical state.

Clients must use scenario-aware Query Layer results rather than infer effective state from canonical building fields.

Persisted scenarios store canonical identifiers, never localized display names.

## Plan Comparison and Decision Summaries

`compare_plans()` generates each side independently through the authoritative planning pipeline and delegates comparison calculations to the comparison module.

`compare_accepted_build_plans(...)` consumes accepted immutable plan inputs and does not regenerate them.

`generate_decision_summary()` delegates planning and comparison, then returns structured facts. Recommendation and presentation remain client responsibilities.

## Resource Ledgers

`generate_resource_ledger()` is the public entry point for income-aware construction and recruitment accounting.

The Query Layer resolves one effective starting state and reuses it throughout plan, income, stock, and ledger generation.

The automatic income model includes certified deterministic town-building income and excludes stochastic or user-unmodeled map income.

Recruitment presentation resolves unit and upgrade names through planner
display-name operations. Localization does not own recruitment availability,
quantity, date, or cost.

## Planner Localization Ownership

The Query Layer owns one immutable Planner Localization Catalog for its
configured language.

The catalog is constructed eagerly during canonical startup from canonical
planner-visible entities and explicit planner localization sources.

The Query Layer must not:

- scan the complete localization directory;
- expose raw token maps;
- expose localization file paths;
- expose source manifests;
- apply file-order conflict resolution;
- use localized names as canonical identity.

The existing localization parser remains an internal backend component with
unchanged duplicate-key semantics.

Changing language constructs a new immutable catalog. It does not mutate the
current catalog, canonical data, planner state, or scenarios.

## Public Contract

Application clients may import supported Query Layer interfaces from `olden_db.query` and documented stable domain contracts from their defining modules.

The Query Layer is the supported application-facing backend entry point.

Internal parser, database, graph, path, planner-algorithm, localization-source,
and catalog-index implementation details remain private to the backend.

## Behavioral Guarantees

- Canonical SIDs and `BuildingKey` values are authoritative identifiers.
- Query operations are deterministic for identical game data and inputs.
- Discovery results are immutable and deterministically ordered.
- Display-name lookups are deterministic for identical data, language, and source policy.
- Display-name lookups always apply the documented fallback order.
- Invalid requests raise documented Query Layer exceptions rather than leaking lower-level lookup failures.
- Canonical initialization is available through `PlanningQueryService.from_default_game_data()`.
- Existing `generate_build_plan(...)` callers remain compatible.
- Existing `get_building_display_text(...)` purpose remains compatible.
- Empty scenarios preserve canonical output.
- Query Layer behavior is independent of UI event frequency and execution scheduling.
- Localization configuration does not change planner, comparison, or persistence identity.

## Compatibility Policy

Documented Query Layer methods, exceptions, stable domain contracts, and behavioral guarantees are public API.

Changes to those contracts require explicit architectural review.

Internal implementation may evolve provided the documented public behavior remains satisfied.

BE-014 may replace the current internal single-file building-localization
dependency with the Planner Localization Catalog while preserving public call
shapes and deterministic fallback.

## Validation

Validation must cover:

- canonical planning;
- initialization and discovery;
- scenario equivalence and overrides;
- `generate_planner_result(...)`;
- diagnostics;
- comparisons and decision summaries;
- resource ledgers;
- faction, building, unit, and upgrade display-name lookup;
- localized success and both fallback levels;
- invalid canonical identity errors;
- deterministic repeated catalog construction and lookup;
- catalog immutability;
- unchanged existing parser duplicate-key tests;
- absence of full-directory planner localization scanning;
- deterministic repeated Query Layer calls;
- compatibility of `generate_build_plan(...)`;
- compatibility of `get_building_display_text(...)`;
- absence of workspace or UI lifecycle state in Query Layer contracts;
- absence of localization storage in public Query Layer contracts.

Use repository-provided test modules with:

```text
python -m scripts...
```
