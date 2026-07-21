# Scenario Comparison Workspace Architecture

## Status

**Decision:** Approved  
**Work item:** ARCH-020 — Scenario Comparison Workspace Architecture  
**Sprint:** 15 — Comparative Planning  
**Depends on:** ARCH-019, BE-010, BE-011, UI-006, UI-007, UI-008  
**Production behavior changed by this document:** None

## Purpose

This document extends the canonical Planning Workspace architecture so that multiple independent planning scenarios can coexist and be compared without introducing multiple planner implementations, duplicate Query Layer services, or competing planning lifecycles.

Each comparison member remains a complete Planning Workspace with its own semantic selection, revision counter, pending state, accepted result, retained-result behavior, and failure state. Comparison is application orchestration over accepted results; it is not a second planner.

## Decision

Adopt an application-scoped `ScenarioComparisonCollection` that owns an ordered set of independent `PlanningWorkspace` instances.

The desktop application continues to own exactly one application-scoped `PlanningQueryService`. Every workspace uses that shared service through the same planning execution boundary established by ARCH-019.

```text
Desktop Application
    owns one PlanningQueryService
    owns one ScenarioComparisonCollection
    owns comparison-level presenter coordination

ScenarioComparisonCollection
    owns ordered PlanningWorkspace instances
    owns comparison membership and ordering
    owns comparison-selection state

PlanningWorkspace A         PlanningWorkspace B
    independent selection       independent selection
    independent revision        independent revision
    independent lifecycle       independent lifecycle
          |                           |
          +------ shared Query Layer-+
                          |
                    shared planner
```

No workspace may mutate, invalidate, advance, or replace another workspace's state.

## Relationship to ARCH-019

ARCH-019 remains authoritative for the lifecycle of an individual Planning Workspace.

ARCH-020 does not replace the ARCH-019 model. It composes multiple instances of that model.

The following ARCH-019 rules remain unchanged for every workspace:

- one semantic planning selection;
- exactly one canonical planning target;
- immutable planning input;
- independent selection revision;
- revision-based stale-result rejection;
- one latest accepted result;
- optional retained previous result;
- canonical failure and diagnostic handling;
- Query Layer-only backend access;
- passive views and immutable presentation contracts.

## Terminology

### Planning Workspace

One independent planning lifecycle defined by ARCH-019. A workspace answers one current planning question for one semantic selection.

### Comparison Collection

An application-level ordered collection of Planning Workspaces that the player wishes to inspect together. The collection owns membership and comparison ordering. It does not own planner rules or workspace-internal lifecycle state.

### Comparison Member

A Planning Workspace participating in a comparison collection.

### Workspace Identity

A stable application identifier that distinguishes one workspace from every other workspace, even when two workspaces contain identical selections.

### Comparison Snapshot

An immutable application snapshot containing the accepted-result state of the selected comparison members at one comparison evaluation point.

### Comparable Result

The accepted result of a workspace, together with the workspace identity, accepted selection snapshot, and accepted revision that produced it.

## Workspace Identity

Each Planning Workspace must have a stable `WorkspaceId` assigned by the application layer.

```text
WorkspaceId
    opaque application identity
```

Requirements:

- identity is unique within the active comparison collection;
- identity does not depend on faction, target, scenario, title, or display order;
- identity survives workspace edits;
- identity is not a canonical game-data identifier;
- identity is not a widget identifier;
- duplicate selections remain distinguishable;
- removal of one workspace does not renumber or redefine the remaining identities.

A human-readable label such as `Scenario A` or `Capitol First` is presentation or persistence metadata and is not the authoritative identity.

## Workspace Collection

The `ScenarioComparisonCollection` owns an ordered collection:

```text
ScenarioComparisonCollection
    workspaces: tuple[PlanningWorkspace, ...]
    active_comparison_members: tuple[WorkspaceId, ...]
```

The exact implementation may use mutable application orchestration internally, but all presenter-facing snapshots must be immutable.

Collection responsibilities:

- create a workspace with a new stable identity;
- duplicate a workspace selection into a new independent workspace;
- remove a workspace;
- preserve deterministic display and comparison order;
- select which workspaces participate in a comparison;
- expose immutable collection snapshots;
- request comparison projection from accepted results.

The collection must not:

- share workspace revision counters;
- copy accepted results by reference as current state for another workspace;
- propagate selection edits between workspaces;
- call planner internals;
- infer plan differences;
- rewrite canonical diagnostics;
- make one workspace's failure block another workspace's execution.

## Workspace Isolation

Every workspace is semantically independent.

Each workspace independently owns:

- `WorkspaceId`;
- `PlanningSelection`;
- selection revision;
- execution status;
- accepted result;
- accepted-result revision;
- retained previous result;
- current failure;
- diagnostics;
- presenter-facing immutable snapshot.

Changing Workspace A must have no semantic effect on Workspace B.

This remains true when:

- both workspaces use the same faction;
- both target the same building;
- both begin with identical scenarios;
- one workspace was duplicated from the other;
- one workspace is pending while another is ready;
- one workspace fails;
- one workspace is removed from the comparison.

Duplication copies semantic input only. It creates a new identity and a new lifecycle. It does not create a shared revision counter or shared accepted-result ownership.

## Planner Sharing

The application must not construct one planner or Query Layer service per workspace.

One application-scoped `PlanningQueryService` serves all workspaces.

Each workspace execution supplies its own immutable selection snapshot to the shared service. The Query Layer remains stateless with respect to workspace identity and comparison membership.

```text
Workspace selection snapshot
    ↓
Planning Execution Coordinator
    ↓
shared PlanningQueryService
    ↓
shared graph / planner / scenario pipeline
    ↓
PlannerResult or documented failure
    ↓
originating workspace only
```

Workspace identity and revision are application orchestration metadata. They must not be passed into planner algorithms unless a future infrastructure need requires opaque correlation outside planning semantics.

## Query Layer

A shared Query Layer instance is the canonical design.

The Query Layer:

- receives normal planning inputs for one workspace at a time;
- remains deterministic for identical immutable inputs;
- returns existing canonical result and failure contracts;
- remains unaware of comparison collection membership;
- does not retain active workspace state;
- does not coordinate workspace lifecycles.

No new Query Layer operation is required merely to host multiple workspaces.

Existing operations remain compatible, including the preferred `generate_planner_result(...)` path for plan and diagnostic state.

A new Query Layer comparison operation is required only when the comparison needs authoritative derived facts not already represented by existing public comparison contracts. Application code must not duplicate backend calculations that already belong to `PlanComparison`, `DecisionSummary`, or another certified backend contract.

## Execution Coordination

ARCH-020 does not authorize asynchronous execution or background planning.

The initial comparison architecture uses the same synchronous execution strategy as ARCH-019.

A single application-scoped execution coordinator may serve all workspaces if it treats each request as independently addressed by:

```text
WorkspaceId
selection revision
immutable PlanningSelection
```

Alternatively, the application may create lightweight per-workspace coordinator state around one shared execution service. Either implementation is acceptable if lifecycle ownership remains independent.

Required acceptance rule:

```text
A completion may update only the workspace whose identity and current revision
match the captured request.
```

A completion for Workspace A can never update Workspace B, even if both selections are identical.

## Independent Lifecycle

Each workspace independently supports the ARCH-019 states:

```text
EMPTY
INCOMPLETE
PENDING
READY
FAILED
```

### Pending state

When one workspace becomes pending:

- other workspaces retain their current statuses;
- accepted results in other workspaces remain valid;
- the comparison view may continue to show ready members;
- the pending workspace may retain its own previous accepted result with explicit retained labeling.

### Accepted state

An accepted result belongs to exactly one workspace identity and one accepted revision.

### Retained-result behavior

A workspace may retain its own previous accepted result while its new selection is pending or failed.

Retained results are not silently eligible for current comparison.

The comparison layer must distinguish:

- current accepted result;
- retained previous result;
- no accepted result.

By default, only current accepted results participate in a current comparison. Historical snapshot comparison requires separate approval.

### Failure

A failure belongs only to the originating workspace.

A failed workspace:

- keeps its canonical failure and diagnostics;
- does not invalidate ready workspaces;
- is excluded from a current accepted-result comparison;
- may continue to display its retained previous result as non-current information.

### Revisions

Revision counters are workspace-local.

There is no collection-wide planning revision that replaces workspace revisions.

The collection may maintain a separate `collection_revision` for membership, ordering, labels, or comparison selection. That revision must not determine whether an individual planning result is current.

## Comparable Result Contract

Comparison must operate on accepted workspace outputs, not on live widget state and not on planner instances.

```text
ComparableWorkspaceResult
    workspace_id
    accepted_selection
    accepted_revision
    planner_result
    optional certified summaries
```

Requirements:

- immutable;
- identifies the source workspace;
- records the accepted selection that produced the result;
- records the accepted revision;
- preserves canonical result objects without rewriting them;
- excludes pending or failed current selections without a current accepted result;
- preserves deterministic collection ordering.

## Comparison Semantics

Comparison is a projection over accepted results.

```text
Independent Planning Workspaces
    ↓
accepted comparable results
    ↓
comparison input snapshot
    ↓
certified comparison operation or presentation projection
    ↓
immutable comparison presentation
```

Comparison must not trigger a different planner implementation.

Comparison must not regenerate plans merely because they are displayed together when accepted results are already available and valid.

### Pairwise comparison

The existing Query Layer supports independent left and right plans through `compare_plans(...)` and structured `PlanComparison` output.

Where accepted `BuildPlan` values already exist, architecture should favor a certified comparison boundary that consumes those accepted plans rather than regenerating them. If the existing public Query Layer cannot compare existing accepted results without re-execution, Backend Engineering should propose a narrowly additive public operation or certified application-facing comparison adapter.

Application presenters must not reproduce action, date, cost, or membership-difference algorithms.

### More than two workspaces

The collection may contain more than two workspaces, but comparison semantics should initially remain explicit and bounded.

Recommended rollout:

- the collection may host multiple independent workspaces;
- Sprint 15 comparison selection chooses exactly two ready members for detailed pairwise comparison;
- additional members remain independently visible;
- future N-way summaries require a separate contract defining ordering, missing-result handling, and derived metrics.

This avoids inventing an implicit N-way recommendation or ranking engine.

### Determinism

For an immutable ordered tuple of comparable accepted results, comparison output must be deterministic.

Determinism includes:

- stable member identity;
- stable left/right role;
- stable comparison ordering;
- stable handling of unavailable members;
- canonical values rather than localized text as identity;
- no dependence on view order unless collection order is explicit comparison input.

## Comparison Readiness

A workspace is current-comparison-ready when:

- its selection is complete;
- its current status is `READY`;
- it has an accepted result for its current selection revision.

A pairwise comparison is ready when exactly two selected members are current-comparison-ready.

Comparison state may be represented as:

```text
INCOMPLETE
READY
UNAVAILABLE
```

Examples:

- one ready member and one pending member → `UNAVAILABLE`;
- two ready members → `READY`;
- fewer than two selected members → `INCOMPLETE`;
- a selected member is removed → membership updates deterministically and becomes `INCOMPLETE` or `UNAVAILABLE`.

The comparison layer must not reinterpret a retained previous result as current readiness.

## Memory Ownership

### Application composition root

Owns:

- one `PlanningQueryService`;
- one `ScenarioComparisonCollection`;
- execution coordination;
- comparison-level presenter wiring;
- application shutdown.

### ScenarioComparisonCollection

Owns:

- workspace instances;
- workspace ordering;
- workspace labels or metadata;
- selected comparison membership;
- collection revision;
- immutable collection snapshots.

### PlanningWorkspace

Owns:

- one semantic planning selection;
- one independent revision lifecycle;
- accepted and retained result state;
- current failure and diagnostics.

### Presenters

Recommended separation:

- one workspace presenter per visible workspace, or one keyed presenter coordinator with strictly partitioned per-workspace state;
- one comparison presenter consuming immutable collection and accepted-result snapshots.

Presenters own orchestration and adaptation, not backend calculations.

### Views

Views are passive.

A workspace view renders one workspace presentation and reports semantic actions with its `WorkspaceId`.

A comparison view renders immutable comparison presentation and reports membership or left/right selection changes.

Views do not own workspaces, accepted results, revision validity, or comparison algorithms.

### Comparison models

Certified backend comparison models remain owned by backend modules and exposed through the Query Layer as documented public contracts.

Immutable comparison presentation models belong to the desktop presentation layer.

The collection may own an immutable comparison snapshot, but it must not own duplicated planner-domain calculations.

## Serialization and Persistence

Comparison persistence is a future additive extension to scenario persistence.

Persistable comparison state may include:

- collection identity where required;
- ordered workspace descriptors;
- stable persisted workspace identities;
- human-readable workspace labels;
- each workspace's semantic `PlanningSelection`;
- each workspace's immutable `PlanningScenario`;
- selected pairwise comparison membership;
- explicit schema version.

Transient state must not be serialized as canonical scenario data:

- pending or execution status;
- in-session revision counters;
- accepted `PlannerResult` objects unless a cache format is separately approved;
- retained previous results;
- current failures;
- in-flight requests;
- focus, expansion, scroll position, or widget state.

On restoration:

1. deserialize and validate semantic collection data;
2. create independent Planning Workspace instances;
3. restore each workspace selection;
4. assign or restore identities according to the persistence contract;
5. re-execute each complete selection through the shared Query Layer;
6. reconstruct accepted results from canonical current data;
7. enable comparison only when selected members are ready.

Persisted data must not allow one workspace to reference another workspace's mutable lifecycle state.

## Compatibility Analysis

This architecture is additive.

### Planning Workspace compatibility

A single-workspace application is a valid `ScenarioComparisonCollection` containing one member.

Existing ARCH-019 behavior remains unchanged when comparison features are not enabled.

### Query Layer compatibility

Existing planning operations remain valid.

One shared `PlanningQueryService` continues to serve the desktop application.

No planner API change is required to create multiple independent workspaces.

A narrowly additive comparison operation may be justified to compare already accepted plans without duplicate regeneration. Such a change must preserve `compare_plans(...)` compatibility.

### Presenter compatibility

The current single-workspace presenter may be retained as the per-workspace presenter and composed by a comparison-level coordinator.

No existing immutable presentation contract should become mutable or comparison-aware merely to support side-by-side rendering.

### View compatibility

Existing single-workspace views may remain valid as reusable workspace panels.

Comparison-specific views consume separate immutable comparison presentation models.

### Persistence compatibility

Existing single-scenario documents remain valid.

A future comparison document must use additive schema versioning or a distinct document type. Existing scenario files must not be reinterpreted as multi-workspace collections without an explicit migration rule.

## Migration Strategy

### Phase 1 — Collection foundation

- introduce `WorkspaceId`;
- introduce `ScenarioComparisonCollection`;
- host the existing Planning Workspace as the first collection member;
- preserve existing single-workspace behavior;
- add immutable collection snapshots.

### Phase 2 — Independent workspace duplication

- add a second workspace by copying semantic selection only;
- assign a new identity and independent revision lifecycle;
- route both workspaces through the shared Query Layer;
- validate failure and pending isolation.

### Phase 3 — Passive side-by-side presentation

- reuse or compose existing workspace presentation contracts;
- add immutable collection-level presentation;
- preserve per-workspace retained-result labeling;
- keep views passive.

### Phase 4 — Pairwise comparison

- select exactly two ready workspace identities;
- build immutable comparable-result snapshots;
- use existing certified comparison contracts where possible;
- add a narrowly scoped backend comparison operation only if accepted results cannot be compared without duplicate planning;
- render comparison output separately from each workspace's own result.

### Phase 5 — Persistence integration

- define a versioned comparison document or additive scenario-document schema;
- persist semantic selections and collection metadata only;
- restore independent workspaces and regenerate results;
- preserve compatibility with existing scenario documents.

### Phase 6 — Future extension

Only through separate approval:

- more than two simultaneously compared members;
- historical snapshot comparison;
- shared resource aggregation;
- recommendation or ranking engines;
- asynchronous execution.

## Incremental Rollout Guidance

The first implementation should support exactly two comparison members while keeping the collection model scalable.

Recommended implementation order:

1. collection and identity contracts;
2. second independent workspace lifecycle;
3. isolation tests;
4. side-by-side workspace presentation;
5. explicit left/right member selection;
6. pairwise comparison using certified contracts;
7. persistence design and migration later.

Do not begin by cloning the planner presenter and editing two independent copies. Reuse one workspace lifecycle abstraction and one shared backend service.

## Risks

### Accidental shared state

Duplicating a workspace may accidentally share mutable selection, presenter, or cached presentation state.

Mitigation: immutable selections, new workspace identity, independent revisions, and keyed presenter state.

### Stale cross-workspace completion

A result could be applied to the wrong workspace if revision alone is used as correlation.

Mitigation: correlate by both `WorkspaceId` and selection revision.

### Duplicate planning during comparison

Using `compare_plans(...)` after both workspaces already hold accepted results may regenerate plans.

Mitigation: define a certified comparison boundary over accepted plans if review confirms duplicate execution is undesirable. Do not reproduce comparison algorithms in presenters.

### Retained-result confusion

A failed or pending workspace may retain a previous result that appears comparable.

Mitigation: current comparison readiness requires a current accepted result. Retained results are explicitly non-current and excluded by default.

### Identity conflation

Display labels or positions may be used as workspace identity.

Mitigation: stable opaque `WorkspaceId`; labels and ordering are metadata.

### Lifecycle duplication

Engineering may create a separate comparison planner lifecycle rather than composing Planning Workspaces.

Mitigation: the collection owns existing workspace instances; comparison consumes their accepted snapshots.

### Persistence overreach

Transient execution state may leak into serialized documents.

Mitigation: serialize semantic selections and collection metadata only, then regenerate canonical results on restore.

### Implicit recommendation behavior

Side-by-side differences may be presented as advice or ranking.

Mitigation: comparison output remains structured deterministic fact. Recommendations and optimization require separate approval.

## Required Validation

Implementation must validate:

- stable unique workspace identity;
- duplicate selections remain independent;
- selection revisions are workspace-local;
- completion correlation uses workspace identity and revision;
- failure in one workspace does not alter another;
- pending state in one workspace does not alter another;
- retained results are excluded from current comparison readiness;
- one shared Query Layer service serves all workspaces;
- no workspace constructs planner or graph internals;
- deterministic left/right comparison for identical accepted inputs;
- immutable collection, workspace, and comparison presentation contracts;
- passive views;
- compatibility of existing single-workspace behavior;
- existing scenario-document compatibility;
- no UI-specific concepts enter backend contracts.

## Non-Goals

This architecture does not approve:

- UI implementation;
- asynchronous execution;
- background workers;
- planner algorithm changes;
- optimization;
- recommendations;
- automatic ranking;
- arbitrary N-way comparison metrics;
- historical-result comparison;
- combined multi-base resource accounting;
- shared mutable workspace selections;
- multiple Query Layer instances per workspace.

## Decision Consequences

## BE-012 Implementation Clarifications

BE-012 keeps `PlanningWorkspace` unchanged and assigns `WorkspaceId` when the
collection creates membership. Collection snapshots contain ordered collection
metadata and each workspace's existing immutable snapshot.

Identity-aware execution captures both `WorkspaceId` and the existing
`PlanningExecutionRequest`. Acceptance resolves the current member by identity
and then delegates revision and selection validation to that member's
`PlanningWorkspace`.

Workspace duplication applies only the source's current semantic
`PlanningSelection` to a new workspace. It does not copy lifecycle state.

One `ScenarioComparisonExecutionCoordinator` serves every workspace through the
application-scoped `PlanningQueryService`.


### Benefits

- multiple planning questions coexist without manual input replacement;
- every scenario remains isolated and reproducible;
- one planner and one Query Layer remain authoritative;
- existing Planning Workspace lifecycle is reused;
- pairwise comparison can consume accepted results;
- single-workspace behavior remains compatible;
- future persistence has a clear semantic boundary.

### Costs

- application orchestration gains collection and identity state;
- presenters must partition state by workspace identity;
- comparison readiness must distinguish current and retained results;
- persistence requires additive versioning;
- a future additive Query Layer comparison operation may be needed to avoid duplicate plan generation.
