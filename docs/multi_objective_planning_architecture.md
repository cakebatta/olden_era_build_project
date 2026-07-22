# Multi-Objective Planning Architecture

## Status

**Decision:** Approved  
**Work item:** ARCH-022 — Multi-Objective Planning Architecture  
**Sprint:** 18 — Planner Experience and Multi-Objective Planning  
**Depends on:** ARCH-021, BE-014, UI-011  
**Production behavior changed by this document:** None  
**Implementation authorized by this document:** No

## Repository Synchronization and Verification

ARCH-022 was designed against the current GitHub `main` documentation and accepted implementation baseline.

The authoritative repository establishes that:

- Sprint 17 is complete;
- ARCH-021, BE-014, and UI-011 are accepted;
- Sprint 18 is the current multi-objective planning milestone;
- the roadmap requires one integrated plan over the union of prerequisite chains;
- Sprint 19 will define multi-town shared-economy architecture;
- current Query Layer planning contracts remain single-target;
- existing Planning Workspace and scenario documents intentionally deferred multi-target semantics;
- no accepted `Objective` or `ObjectiveSet` architecture or implementation already exists.

No newer architectural document supersedes ARCH-022.

ARCH-022 resolves the previously deferred multi-target semantics and supersedes only the single-target limitations in existing planner documentation. Unrelated lifecycle, scenario, Query Layer, localization, comparison, and persistence boundaries remain in force.

## Purpose

The current planner answers:

> How do I build this building?

The next planning contract answers:

> How do I satisfy this complete deterministic objective set for one town?

Example:

```text
Treasury
Mage Guild III
Tier 6 Dwelling
```

The planner produces one integrated legal schedule. It does not generate independent plans and concatenate them.

## Decision

Introduce these canonical immutable contracts:

```text
Objective
ObjectiveSet
TownState
TownPlanningRequest
ObjectiveCompletion
ObjectiveDependencySummary
BuildStepObjectiveProvenance
MultiObjectivePlannerResult
ObjectivePlanningRequestError hierarchy
ObjectivePlanningFailure hierarchy
```

Canonical flow:

```text
TownPlanningRequest
    owns TownState
    owns ObjectiveSet
        ↓
Query Layer validation
        ↓
effective starting-state resolution
        ↓
one prerequisite union
        ↓
one deterministic schedule
        ↓
one resource timeline
        ↓
MultiObjectivePlannerResult
```

## Ownership

The authoritative ownership hierarchy is:

```text
Scenario
    owns Towns

Town
    owns ObjectiveSet

ObjectiveSet
    owns Objective values

TownPlanningRequest
    owns TownState
    owns ObjectiveSet

Planner
    consumes TownPlanningRequest

Planner
    returns MultiObjectivePlannerResult

Query Layer
    owns public validation and invocation

Presenter
    consumes immutable result contracts

View
    receives display-ready presentation models
```

`ObjectiveSet` does not own town identity, starting state, economy, schedule, or presentation.

`TownPlanningRequest` owns—not merely references as an unrelated argument—the complete immutable town intent required by the planner.

## Objective Interface

### Closed tagged union

`Objective` is a closed tagged union of approved immutable objective variants.

Conceptually:

```python
Objective = (
    BuildingCompletionObjective
    | FutureApprovedObjectiveVariant
)
```

This is a domain union, not an alias:

```text
Objective != BuildingKey
```

The initial architecture is:

```text
Objective
├── BuildingCompletionObjective
└── future approved typed variants
```

A mutable plugin registry, generic string type, free-form mapping, UI object, or presenter-defined objective is prohibited.

### Initial variant

```python
@dataclass(frozen=True, slots=True, order=True)
class BuildingCompletionObjective:
    building: BuildingKey
```

A building upgrade uses the canonical upgraded `BuildingKey`.

A separate Upgrade Objective is unnecessary while upgrade completion is already represented by canonical building level identity. A distinct future upgrade contract may be added only if canonical game semantics require behavior beyond building completion.

### Future variants

Every future variant must define:

- canonical identity;
- deterministic ordering key;
- owning town compatibility;
- validation;
- graph or scheduling contribution;
- completion predicate;
- resource semantics;
- objective provenance;
- typed diagnostics and failures;
- Query Layer exposure;
- persistence representation when authorized;
- localization mapping without localized identity.

## Objective Identity and Validation

Objective identity is the complete immutable tagged value.

For a building objective:

```text
type = BUILDING_COMPLETION
target = BuildingKey
```

Two identical building objective values are duplicate identities.

Validation covers:

- supported variant;
- canonical target shape;
- target existence;
- town compatibility;
- parameter ranges;
- internal consistency.

Loaded-data validation occurs through the Query Layer or domain validator because dataclass construction alone cannot confirm canonical existence.

## ObjectiveSet

Conceptual contract:

```python
@dataclass(frozen=True, slots=True)
class ObjectiveSet:
    objectives: tuple[Objective, ...]
```

The Objective Set owns:

- membership;
- exact duplicate normalization;
- deterministic ordering;
- structural compatibility validation;
- immutable iteration.

It does not own:

- TownState;
- PlanningScenario;
- starting date;
- graph construction;
- schedule generation;
- resources;
- localization;
- UI order.

### Invariants

- The set is non-empty for a valid planning request.
- Exact duplicate identities are normalized away.
- Input order does not affect equality or planning.
- Distinct explicit objectives remain present even when one implies another.
- All initial building objectives belong to the same town faction.
- Every objective type defines a total canonical sort key.

A lower-level building objective remains explicit even when a higher level depends on it. Graph actions are deduplicated, but explicit player objectives and their completion facts are preserved.

## TownState

Conceptually:

```python
@dataclass(frozen=True, slots=True)
class TownState:
    faction: str
    starting_date: GameDate
    planning_scenario: PlanningScenario
```

`TownState` represents one town's deterministic planning context.

It does not include:

- workspace revision;
- shared multi-town resources;
- presentation language;
- localization;
- optimization preferences.

## TownPlanningRequest

Canonical contract:

```python
@dataclass(frozen=True, slots=True)
class TownPlanningRequest:
    town_state: TownState
    objective_set: ObjectiveSet
```

The planner consumes this object.

No planner-domain operation accepts an unrelated list of Objective values alongside separate town arguments.

A Query Layer convenience method may accept fields separately only by immediately constructing and validating this request.

## Dependency Union

For each Objective:

1. resolve its canonical target;
2. apply the request's effective starting state;
3. compute its prerequisite closure;
4. add nodes and edges to one integrated graph;
5. record objective provenance for each included node.

Canonical graph identity deduplicates shared prerequisites.

A shared prerequisite:

- appears once in the graph;
- appears once in the schedule;
- costs resources once;
- changes income once;
- may be required by multiple objectives.

Independent subplans are never generated and merged afterward.

## Provenance

The planner preserves why every graph node and scheduled step exists.

### Objective-facing provenance

```python
@dataclass(frozen=True, slots=True)
class ObjectiveDependencySummary:
    objective: Objective
    required_buildings: tuple[BuildingKey, ...]
    constructed_buildings: tuple[BuildingKey, ...]
    satisfied_at_start: tuple[BuildingKey, ...]
```

This answers:

```text
Treasury requires:
    Marketplace
    City Hall
```

### Build-step-facing reverse provenance

```python
@dataclass(frozen=True, slots=True)
class BuildStepObjectiveProvenance:
    building: BuildingKey
    required_by: tuple[Objective, ...]
    objective_targets: tuple[Objective, ...]
```

This answers:

```text
Marketplace

required_by:
    Treasury
    Resource Silo
```

`required_by` contains every explicit Objective whose prerequisite closure includes the building.

`objective_targets` contains every explicit Objective directly completed by that building.

Both tuples use canonical Objective Set ordering.

This provenance is authoritative result data. Presenters must not reconstruct it by traversing planner graphs.

## Scheduling

The planner produces one legal topological schedule over the integrated graph.

Every prerequisite precedes its dependent.

Every unsatisfied required building appears once.

Existing one-town construction limits remain unchanged.

When multiple legal next steps exist, an approved total deterministic tie-breaker is used. Objective input order does not affect the result.

This is deterministic planning, not optimization.

## Economy

Cost, deterministic income, and resource availability are calculated over the integrated chronological schedule.

The result does not sum independently calculated objective costs or ledgers.

A shared income building affects later actions once, regardless of how many objectives require it.

## Objective Completion

Conceptual contract:

```python
@dataclass(frozen=True, slots=True)
class ObjectiveCompletion:
    objective: Objective
    completed: bool
    completion_date: GameDate | None
    satisfied_at_start: bool
    completing_action: BuildingKey | None
```

Completion is derived from the integrated schedule.

An objective already satisfied by effective starting state completes at the request's starting state and creates no build action or cost.

The request is complete only when every explicit Objective completes.

## MultiObjectivePlannerResult

Conceptual immutable contract:

```python
@dataclass(frozen=True, slots=True)
class MultiObjectivePlannerResult:
    request: TownPlanningRequest
    plan: BuildPlan
    objective_completions: tuple[ObjectiveCompletion, ...]
    objective_dependencies: tuple[ObjectiveDependencySummary, ...]
    step_provenance: tuple[BuildStepObjectiveProvenance, ...]
    daily_construction_schedule: tuple[DailyConstructionCost, ...]
    resource_timeline: tuple[ResourceTimelineEntry, ...]
    diagnostics: tuple[PlannerDiagnostic, ...]
    completion_state: ObjectiveSetCompletionState
```

Required semantics:

- one integrated schedule;
- every required action appears once;
- every explicit Objective has one completion entry;
- both provenance directions are immutable;
- total cost is the integrated plan total;
- resource timeline follows the integrated schedule;
- diagnostics preserve canonical attribution;
- COMPLETE means every explicit Objective completed.

## Typed Request Failures

Invalid requests raise typed Query Layer errors.

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

Exact duplicate objectives are normalized away and do not produce an error.

`IncompatibleObjectivesError` applies to distinct objectives that cannot coexist in one valid request.

Each public type must document:

- triggering condition;
- canonical affected Objective values;
- canonical affected entities;
- stable public meaning.

## Typed Infeasibility

A valid request that cannot produce a complete plan returns a typed immutable failure outcome.

Required conceptual hierarchy:

```text
ObjectivePlanningFailure
├── UnsatisfiedPrerequisites
├── NoLegalIntegratedOrder
├── ResourceInfeasibility
└── ObjectiveNotCompletable
```

Each failure contains:

- failure kind;
- affected objectives;
- affected canonical entities;
- immutable diagnostics;
- no localized identity.

Equivalent conditions must consistently use either request errors or failure outcomes according to the documented category.

Unexpected invariant violations are programming defects, not user-facing infeasibility.

## Query Layer

Canonical additive operation:

```text
generate_objective_plan(
    request: TownPlanningRequest
) -> MultiObjectivePlannerResult
```

The Query Layer owns:

- request validation;
- canonical target validation;
- effective starting-state resolution;
- planner invocation;
- typed request-error translation;
- typed infeasibility return;
- immutable result publication.

It hides:

- graph traversal;
- union construction;
- provenance algorithms;
- schedule internals;
- resource calculation internals.

## Additive Compatibility

Existing operations remain public:

```text
generate_build_plan(...)
generate_planner_result(...)
```

They are compatibility adapters equivalent to:

```python
TownPlanningRequest(
    town_state=TownState(...),
    objective_set=ObjectiveSet(
        objectives=(
            BuildingCompletionObjective(
                BuildingKey(faction, sid, level)
            ),
        )
    ),
)
```

One-objective results preserve existing:

- build steps;
- dates;
- total cost;
- completion date;
- daily construction schedule;
- diagnostics;
- PlanningScenario behavior.

No existing API is removed or broken by ARCH-022.

Objective-set comparison, persistence migration, and UI behavior require later authorized work.

## Workspace Integration

A complete Planning Selection owns one Town Planning Request.

Objective addition, removal, or replacement is one semantic selection mutation and increments the workspace revision.

Workspace lifecycle remains unchanged:

- incomplete;
- pending;
- ready;
- failed;
- retained previous result;
- stale-completion rejection.

UI selection order is not Objective Set ordering.

## Future Multi-Town Compatibility

Target hierarchy:

```text
Scenario
└── Town
    └── ObjectiveSet
        ├── Objective
        ├── Objective
        └── Objective
```

Future request direction:

```python
@dataclass(frozen=True, slots=True)
class ScenarioPlanningRequest:
    shared_economy: SharedEconomy
    towns: tuple[TownPlanningIntent, ...]

@dataclass(frozen=True, slots=True)
class TownPlanningIntent:
    town_id: TownId
    town_state: TownState
    objective_set: ObjectiveSet
```

Sprint 19 adds:

- Scenario ownership;
- Town identity;
- shared resources;
- aggregate income;
- coordinated scheduling;
- cross-town contention;
- scenario completion.

It reuses without redesign:

- Objective union;
- ObjectiveSet;
- TownState;
- objective validation;
- completion predicates;
- provenance semantics;
- Query Layer ownership;
- canonical localization rules.

The multi-town scheduler must coordinate eligible actions across towns against one shared ledger. It must not finalize independent town schedules and concatenate them.

## Out of Scope

ARCH-022 does not authorize:

- backend implementation;
- UI behavior;
- clickable plan steps;
- explanation presentation;
- optimization;
- multi-town implementation;
- shared-economy scheduling;
- persistence changes;
- comparison changes;
- presentation changes;
- objective prioritization;
- optional or weighted objectives;
- partial success presented as complete.

## Follow-On Backend Guidance

A future backend work order should:

1. define the closed Objective union;
2. implement BuildingCompletionObjective;
3. implement ObjectiveSet normalization;
4. implement TownState and TownPlanningRequest;
5. generalize graph construction to multiple roots;
6. preserve provenance in both directions;
7. reuse existing planner and economy behavior;
8. derive ObjectiveCompletion values;
9. implement typed request errors;
10. implement typed infeasibility outcomes;
11. expose generate_objective_plan(request);
12. retain existing API adapters;
13. preserve existing regression behavior.

## Validation Requirements

Future implementation must validate:

- Objective is not equivalent to BuildingKey;
- unsupported Objective variants fail explicitly;
- ObjectiveSet immutability;
- duplicate normalization;
- deterministic ordering;
- request ownership of ObjectiveSet;
- typed request errors;
- typed infeasibility outcomes;
- shared prerequisite appears once;
- shared prerequisite is charged once;
- objective-facing provenance;
- reverse build-step provenance;
- one-objective equivalence;
- multi-objective integrated scheduling;
- objective completion timing;
- starting-state completion;
- full completion invariant;
- integrated resource timeline;
- no independent-plan concatenation;
- unchanged existing API behavior;
- future multi-town composition without changing ObjectiveSet.

## Acceptance

ARCH-022 is complete when documentation establishes:

- a real typed Objective interface;
- explicit ownership from Scenario through Planner Result;
- TownPlanningRequest ownership of ObjectiveSet;
- bidirectional prerequisite provenance;
- additive Query Layer APIs;
- typed request and infeasibility failures;
- single-target compatibility;
- deterministic dependency-union planning;
- a stable future multi-town seam.
