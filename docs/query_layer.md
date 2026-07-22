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

The Query Layer may coordinate database, graph, planner, objective-planning, scenario, comparison, decision-summary, recruitment-stock, resource-ledger, diagnostic, and planner-localization modules; validate requests; return deterministic domain objects; and expose canonical discovery information.

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

## Multi-Objective Planning Interface

ARCH-022 defines one canonical public request contract:

```python
@dataclass(frozen=True, slots=True)
class TownPlanningRequest:
    town_state: TownState
    objective_set: ObjectiveSet
```

For the initial single-town implementation, `TownState` conceptually owns:

```text
faction
starting_date
PlanningScenario
```

The request owns the Objective Set as an immutable field. The planner does not
accept an unrelated list of targets.

The canonical additive Query Layer operation is:

```text
generate_objective_plan(
    request: TownPlanningRequest
) -> MultiObjectivePlannerResult
```

Convenience methods may accept the request's fields separately only when they
immediately construct a `TownPlanningRequest` and delegate to the canonical
operation. They are adapters, not alternative planner contracts.

The Query Layer guarantees:

- request validation occurs before planning;
- every objective belongs to the request town;
- shared prerequisites are solved once;
- one integrated build schedule is returned;
- objective completion facts are immutable and canonical;
- build-step-to-objective provenance is returned;
- deterministic tie-breaking is documented and stable;
- localization is not part of request or result identity;
- typed validation failures remain distinct from typed infeasibility outcomes.

## Objective Interface

`Objective` is a closed tagged union of approved immutable objective variants.

Initial public variant:

```python
@dataclass(frozen=True, slots=True, order=True)
class BuildingCompletionObjective:
    building: BuildingKey
```

Conceptually:

```text
Objective
├── BuildingCompletionObjective
└── future approved Objective variants
```

A future objective variant must define:

- canonical identity;
- total deterministic ordering;
- town compatibility;
- prerequisite or schedule contribution;
- completion predicate;
- provenance semantics;
- diagnostic attribution;
- resource semantics.

No generic string objective, untyped mapping, UI object, or mutable plugin
registry is part of the public contract.


## Objective Intent Invariant

An `ObjectiveSet` describes required end-state outcomes.

The Query Layer must not interpret:

- objective insertion order;
- UI selection order;
- normalized tuple order;
- display order;

as requested execution order or priority.

`generate_objective_plan(...)` delegates execution strategy to the planner.
Construction sequence is determined only by canonical legality, effective
starting state, approved scheduling constraints, deterministic economy, and the
planner's documented tie-breaker.

Future user-authored priorities, deadlines, or ordering constraints require
separate typed request fields and separate architectural approval.

## Planning Interface

Supported planning operations include:

- `get_building(...) -> BuildingLevel`
- `get_prerequisites(...) -> tuple[BuildingLevel, ...]`
- `get_prerequisite_statuses(..., scenario=None) -> tuple[PrerequisiteStatus, ...]`
- `generate_build_plan(..., scenario=None) -> BuildPlan`
- `generate_planner_result(..., scenario=None) -> PlannerResult`
- `generate_objective_plan(request) -> MultiObjectivePlannerResult`
- `get_cumulative_cost(..., scenario=None) -> ResourceCost`
- `enumerate_build_orders(..., scenario=None) -> tuple[tuple[BuildingKey, ...], ...]`
- `compare_plans(...) -> PlanComparison`
- `compare_accepted_build_plans(...) -> BuildPlanComparisonOutcome`
- `generate_decision_summary(...) -> DecisionSummary`
- `generate_resource_ledger(...) -> ResourceLedger`

`generate_build_plan(...)` and `generate_planner_result(...)` remain supported as additive compatibility adapters.

They are semantically equivalent to constructing a `TownPlanningRequest` with a
one-member Objective Set containing one `BuildingCompletionObjective`.

They must not be removed, change call shape, or produce different one-target
behavior without separate deprecation architecture.

The preferred new application workflow uses `generate_objective_plan(...)`.

When `PlanningScenario` is empty or omitted, planning remains equivalent to canonical planning.

Localization configuration must not alter any planning result.

## Planning Workspace Relationship

The Planning Workspace is application orchestration.

ARCH-022 supersedes the former one-target selection limitation.

A complete workspace selection owns one `TownPlanningRequest`.

The Query Layer does not receive:

- selection revision counters;
- widget state;
- debounce configuration;
- workspace layout;
- pending-state metadata;
- stale-result policy.

Continuous replanning, execution timing, and completion acceptance remain application concerns.

A future multi-town operation will be additive and separately approved. It will coordinate multiple town requests against one shared economy rather than concatenate independently accepted plans.

## Scenario Comparison Relationship

Scenario comparison is application collection state.

Existing accepted single-target comparison operations remain public and compatible.

Objective-set comparison requires a later additive contract because objective membership, objective completion timing, and provenance introduce new comparison dimensions.

ARCH-022 does not alter existing comparison APIs.

## Scenario-Aware Planning

`PlanningScenario` is immutable and contains deterministic starting-building overrides identified by canonical `BuildingKey` values.

The Query Layer resolves the effective immutable starting-building set once for the Town Planning Request.

An empty `PlanningScenario()` is behaviorally equivalent to canonical planning.

Persisted scenarios continue to store canonical identifiers, never localized display names.

The existing `PlanningScenario` remains a single-town starting-state contract. A future aggregate scenario owns towns and shared economy and must not overload this contract without separate architecture.

## Typed Validation Failures

Invalid requests raise explicit Query Layer validation errors.

Required conceptual hierarchy:

```text
ObjectivePlanningRequestError
├── EmptyObjectiveSetError
├── UnsupportedObjectiveTypeError
├── UnknownObjectiveTargetError
├── CrossTownObjectiveError
├── IncompatibleObjectivesError
├── InvalidTownStateError
├── InvalidStartingDateError
└── IncompatiblePlanningScenarioError
```

Exact class names may follow repository conventions, but one documented public
type must exist for each semantic category.

Exact duplicate objective identities are normalized away and therefore are not
an error.

`IncompatibleObjectivesError` is reserved for distinct objective values that
cannot participate in one valid Town Planning Request.

## Typed Infeasibility Outcomes

A structurally valid request that cannot produce a complete plan returns a typed
immutable infeasibility contract rather than a request-validation exception.

Required conceptual categories:

```text
ObjectivePlanningFailure
├── UnsatisfiedPrerequisites
├── NoLegalIntegratedOrder
├── ResourceInfeasibility
└── ObjectiveNotCompletable
```

Each failure includes:

- canonical failure kind;
- affected objectives;
- affected canonical entities where applicable;
- immutable diagnostics;
- no localized identity.

Equivalent conditions must not unpredictably alternate between exceptions and
failure results.

Unexpected invariant violations remain programming defects and are not ordinary
planner failures.

## Provenance Contract

The result exposes both directions of objective provenance.

Objective-facing:

```text
ObjectiveDependencySummary
    objective
    required_buildings
    constructed_buildings
    satisfied_at_start
```

Build-step-facing:

```text
BuildStepObjectiveProvenance
    building
    required_by
    objective_targets
```

`required_by` contains every explicit Objective whose prerequisite closure
contains the building.

`objective_targets` contains every explicit Objective directly satisfied by
that building.

Both tuples use canonical Objective Set ordering.

Presenters may format these facts but may not infer them from graph traversal.

## Result Contract

`MultiObjectivePlannerResult` is immutable and includes:

```text
request
integrated BuildPlan
objective completions
objective-facing dependency summaries
build-step-facing provenance
daily construction schedule
resource timeline or approved immutable resource projection
diagnostics
completion state
```

A result is complete only when every explicit Objective is complete.

The integrated total cost is authoritative and is never calculated by summing
independent objective plans.

## Resource Ledgers

Multi-objective resource behavior derives from the one integrated schedule.

The Query Layer must not generate one ledger per Objective and add them together.

Existing resource-ledger APIs remain compatible until separately evolved.

## Planner Localization Ownership

Objective identity remains canonical.

Building Objective display uses existing Planner Localization Catalog operations.

Future Objective variants must define their presentation mapping without storing localized strings in Objective values.

## Public Contract

Application clients may import supported Query Layer interfaces and documented stable domain contracts.

Graph union, prerequisite traversal, provenance construction, planner algorithms,
localization storage, and typed failure implementation details remain private.

## Behavioral Guarantees

- Objective is a typed union, not an alias for BuildingKey.
- TownPlanningRequest owns one ObjectiveSet.
- ObjectiveSet owns normalized immutable Objective membership.
- ObjectiveSet expresses desired end state and never execution order.
- Multi-objective planning produces one integrated plan.
- Shared prerequisites are scheduled and charged once.
- Reverse build-step provenance is authoritative result data.
- Validation failures and infeasibility outcomes are typed separately.
- Existing single-target APIs remain additive compatibility adapters.
- Query operations are deterministic for identical canonical inputs.
- Localization does not change objective identity or planning output.

## Compatibility Policy

Documented existing Query Layer methods remain public API.

`generate_objective_plan(...)` is additive.

Single-target methods delegate conceptually to a one-objective request and remain compatible until a separately approved deprecation and migration plan exists.

## Validation

Validation must cover:

- immutable Objective variants;
- closed-union exhaustiveness;
- immutable normalized Objective Sets;
- exact duplicate normalization;
- deterministic canonical ordering;
- typed request-validation errors;
- typed infeasibility outcomes;
- cross-town and unknown-target rejection;
- incompatible-objective rejection;
- one-objective equivalence with existing APIs;
- shared-prerequisite deduplication;
- shared cost and income application once;
- objective-facing provenance;
- build-step-facing reverse provenance;
- deterministic objective completion;
- integrated total cost and resource timeline;
- no independent-plan concatenation;
- unchanged existing single-target call shapes and behavior;
- Query Layer-only application access;
- localization independence.

Use repository-provided test modules with:

```text
python -m scripts...
```

## BE-014 Planner Localization Catalog Implementation

Canonical startup parses one explicit planner-localization source document and constructs one immutable `PlannerLocalizationCatalog`. The builder enumerates only planner-visible canonical factions, buildings, units, and upgrades from `LoadedGameData`; unrelated interface tokens are not copied into planner indexes.

Public display-name operations are `get_faction_display_name(...)`, `get_building_display_name(...)`, `get_unit_display_name(...)`, and `get_upgrade_display_name(...)`. Existing display-text operations remain compatible and delegate to the catalog.
