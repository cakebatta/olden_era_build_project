# Desktop Application Architecture Specification

## Purpose

This document defines architectural boundaries for the desktop application built on the Query Layer.

The desktop makes deterministic planning workflows accessible without coupling presentation code to parser, database, graph, localization, path, or planner-algorithm internals.

User-facing workflows are documented separately.

## Architectural Position

```text
Game Assets
    ↓
Backend Parsers and Models
    ↓
Planning, Economy, and Diagnostic Algorithms
    ↓
Query Layer
    ↓
Planning Workspaces and Application Orchestration
    ↓
Desktop Presenters and Views
```

The desktop application is a client of the Query Layer.

It may use documented stable contracts accepted or returned by the Query Layer, but it must not invoke internal backend modules directly.

## Current Product Direction

The primary desktop workflow is an interactive Planning Workspace.

The user should be able to:

- discover factions and buildings;
- select one canonical planning target per active workspace;
- change hypothetical starting state;
- receive automatic plan and diagnostic updates;
- inspect construction steps, dates, costs, and completion information;
- revise the selection without repeatedly invoking a separate Generate action;
- retain a clearly marked previous summary while a replacement is pending;
- maintain multiple independent planning scenarios;
- compare current accepted results without creating another planner lifecycle.

Sprint 13 established one single-target Planning Workspace. Sprint 15 extends the application by composing multiple independent workspaces. Multi-target planning, asynchronous execution, recommendation behavior, and combined resource aggregation remain separate work.

## Technology Decision

Use the Python standard-library `tkinter` toolkit unless concrete requirements justify a reviewed change.

The application should continue to prefer minimal dependencies and explicit ownership.

## Application Structure

Preferred package responsibilities:

```text
olden_db/
    desktop/
        app.py
        state.py
        workspace.py
        execution.py
        comparison.py
        views/
        presenters/
        formatting.py
```

Exact filenames may evolve, but responsibilities must remain separated.

### Application startup

Owns root-window creation, one application-scoped `PlanningQueryService`, the active `ScenarioComparisonCollection`, execution coordination, top-level dependency wiring, navigation, and shutdown.

### Workspace and state

Own semantic application state:

- active Planning Workspace instances;
- stable workspace identities;
- immutable planning selections;
- workspace-local selection revisions;
- workspace-local execution status;
- latest accepted results;
- current failures;
- comparison membership and ordering;
- transient UI-independent workspace state.

It must not store widgets, localized labels as identity, or planner algorithms.

Do not introduce a generic state-management framework.

### Execution coordination

Owns when Query Layer planning is invoked and whether a completion is still current.

Execution captures:

```text
WorkspaceId
immutable PlanningSelection
selection revision
```

A completion may update only the originating workspace whose current revision matches the captured revision.

The initial implementation uses synchronous calls and revision-based stale-result protection.

Debounce, background execution, and cooperative cancellation remain deferred until measured responsiveness requires them.

### Views

Own widget construction, accessibility, focus, local interaction mechanics, display, and validation messages.

Views report semantic actions. They must not implement planning rules, result-validity rules, comparison calculations, or query backend internals.

Workspace views report their `WorkspaceId` with semantic actions. Comparison views report comparison-member or left/right selection changes.

### Presenters

Own coordination between views, collection state, individual workspace state, execution coordination, and `PlanningQueryService`.

Presenters may:

- translate UI actions into semantic selection commands;
- apply workspace mutations;
- request execution;
- translate documented Query Layer errors;
- supply immutable presentation models;
- render pending, ready, failed, and retained-previous-result states;
- construct immutable comparison input snapshots from current accepted results;
- adapt certified comparison results for passive views.

Presenters must not derive prerequisite legality, costs, diagnostics, effective scenario state, plan differences, rankings, or recommendations.

Use plain Python presenter classes. Do not introduce MVVM frameworks or global event buses.

### Formatting

Owns pure presentation formatting for stable public domain contracts, including resource costs, game dates, building identities, plan steps, diagnostics, workspace statuses, and certified comparison facts.

## Sprint 13 Desktop Integration

The desktop composition root constructs exactly one `PlanningWorkspace` and one `PlanningExecutionCoordinator` for the application session. The planner presenter receives both dependencies and never constructs replacements.

Discrete semantic changes to faction, canonical target, starting date, or `PlanningScenario` replace the immutable `PlanningSelection`. Complete selections execute immediately and synchronously through the coordinator. Compound scenario restoration is applied as one semantic replacement and therefore executes once.

The desktop renders immutable workspace snapshots as incomplete, pending, ready, failed, or retained-previous-result presentation. A retained result is never labeled current. The legacy Generate control is hidden and disabled.

## Sprint 14 Persistent Planning Summary

The planner presenter maps immutable Planning Workspace snapshots into an immutable `PlanningSummaryPresentation`. Values come only from the accepted `PlannerResult`, BE-011 `daily_construction_schedule`, the Query Layer localization operation, and existing diagnostic adapters.

The presenter caches localized text and suppresses view updates when the full immutable presentation is unchanged. The view renders labels and grouping only; it does not derive schedules, dates, costs, diagnostics, or localization. A retained result is always labeled `Previous Accepted Plan`.

## Sprint 15 Scenario Comparison Composition

ARCH-020 composes multiple complete Planning Workspace instances under one application-scoped `ScenarioComparisonCollection`.

Each workspace has a stable opaque `WorkspaceId` and independently owns:

- its `PlanningSelection`;
- selection and accepted-result revisions;
- pending, ready, and failed lifecycle;
- accepted and retained results;
- failures and canonical diagnostics.

Duplicating a workspace copies semantic input only. It creates a new identity, a new revision lifecycle, and independent result ownership.

The application constructs one `PlanningQueryService` and shares it across all workspaces. The Query Layer remains unaware of workspace identity, collection membership, and presentation order.

Every planning execution is correlated by both `WorkspaceId` and selection revision. A completion may update only the originating workspace whose revision still matches.

The collection may contain multiple workspaces, but the initial detailed comparison selects exactly two current-ready members with explicit left and right roles. Other members remain independent and visible.

Only current accepted results are comparison-ready. A retained previous result remains displayable but is excluded from current comparison by default.

The comparison presenter consumes immutable accepted-result snapshots and certified backend comparison contracts. It must not reproduce action, date, cost, membership-difference, recommendation, or ranking algorithms.

Workspace views remain passive reusable panels. A comparison view receives a separate immutable comparison presentation and reports only semantic member or left/right selection actions.

See `docs/scenario_comparison_architecture.md`.

## Planning Workspace Ownership

```text
Application
    owns one PlanningQueryService
    owns one ScenarioComparisonCollection
    owns PlanningExecutionCoordinator
    owns workspace presenter coordination
    owns ComparisonPresenter

ScenarioComparisonCollection
    owns ordered PlanningWorkspace instances
    owns stable WorkspaceId values
    owns comparison membership and ordering
    owns collection-level immutable snapshots

PlanningWorkspace
    owns one semantic selection
    owns workspace-local revisions
    owns accepted results and current failures
    owns retained previous result state

PlanningExecutionCoordinator
    captures workspace identity and immutable selection snapshots
    calls shared PlanningQueryService
    rejects stale or misaddressed completions

WorkspacePresenter
    handles semantic actions for one WorkspaceId
    renders one workspace snapshot

ComparisonPresenter
    consumes immutable collection and accepted-result snapshots
    invokes certified comparison boundaries
    renders immutable comparison presentation

Views
    own widgets
    report semantic user actions
    render supplied presentation models
```

Prefer explicit callbacks over a global event bus.

## Planning Selection

One workspace contains exactly one requested canonical target plus its starting date and immutable `PlanningScenario`.

The planning model must not contain:

- checkbox variables;
- widget IDs;
- drag coordinates;
- mouse or keyboard events;
- localized names as identity.

Changing interaction mechanisms must not require planner or Query Layer redesign.

## Workspace Identity

Every workspace has a stable opaque `WorkspaceId`.

Requirements:

- identity is independent of faction, target, scenario, label, and display position;
- identical selections remain distinguishable;
- workspace edits do not change identity;
- removing a workspace does not renumber remaining identities;
- labels such as `Scenario A` are metadata, not identity;
- widget identifiers are never authoritative workspace identity.

## Revision and Result Lifecycle

Every semantic selection mutation increments only that workspace's selection revision.

Execution captures workspace identity, immutable selection, and revision.

A completion is accepted only when both:

- its `WorkspaceId` matches the destination workspace;
- its revision still matches the current selection.

Older or misaddressed completions are discarded.

Recommended statuses:

```text
EMPTY
INCOMPLETE
PENDING
READY
FAILED
```

The latest accepted result may remain visible while a replacement is pending or after the current request fails, but the view must identify it as retained previous information rather than current output.

Each workspace owns this lifecycle independently. One workspace becoming pending or failed must not change another workspace's status or accepted result.

## Comparison Readiness

A workspace is current-comparison-ready when:

- its selection is complete;
- its current status is `READY`;
- it has an accepted result for its current selection revision.

A pairwise comparison is ready when exactly two selected workspace identities are current-comparison-ready.

Comparison state may be represented as:

```text
INCOMPLETE
READY
UNAVAILABLE
```

A retained previous result is not current-comparison-ready.

## Query Layer Integration

All backend operations must use documented Query Layer methods.

The desktop may import documented stable public domain contracts. It must not import parser, unit parser, database, graph, localization, path, or planner-algorithm internals.

Missing capabilities must be reported and addressed through a reviewed Query Layer evolution.

Continuous replanning and comparison collection membership are application concerns. Query Layer operations remain stateless and deterministic.

One application-scoped Query Layer service serves every workspace.

Where accepted `BuildPlan` values already exist, comparison should use a certified boundary that consumes those accepted plans rather than regenerate them. If the public Query Layer cannot support this without duplicate execution, Backend Engineering should propose a narrowly additive operation while preserving existing `compare_plans(...)` compatibility.

## Scenario Integration

Each workspace owns its own immutable `PlanningScenario`.

The Query Layer remains authoritative for effective starting-building state.

A scenario edit creates a new planning selection revision and triggers replanning when the selection is complete.

Scenario state is not inferred from canonical building fields.

No workspace's scenario may influence another workspace.

## Multi-Base and Multi-Scenario Direction

The comparison collection is an ordered set of independent Planning Workspaces with stable application identities.

The product may initially expose two comparison members and later host additional workspaces without changing planner algorithms.

Per-workspace results remain authoritative and distinct.

Future combined resource summaries require a separate deterministic aggregation contract and must preserve workspace attribution.

Detailed comparison initially remains pairwise. Arbitrary N-way comparison, ranking, and recommendation semantics require separate approval.

## Serialization and Persistence

Comparison persistence is a future additive extension to scenario persistence.

Persistable state may include:

- ordered workspace descriptors;
- stable persisted workspace identities;
- human-readable labels;
- each workspace's semantic `PlanningSelection`;
- each workspace's immutable `PlanningScenario`;
- selected pairwise comparison membership;
- schema version.

Transient state must not be persisted as canonical scenario data:

- pending status;
- in-session revision counters;
- accepted `PlannerResult` objects unless a cache contract is separately approved;
- retained previous results;
- current failures;
- in-flight requests;
- focus, expansion, scrolling, or widget state.

On restoration, the application reconstructs independent workspaces and regenerates each complete selection through the shared Query Layer.

Existing single-scenario documents remain valid. Comparison persistence must use additive schema versioning or a distinct document type.

## Localization

Canonical identifiers remain the source of identity.

Localized names are supplementary presentation and must never become lookup keys.

Localized workspace labels are presentation metadata and do not replace `WorkspaceId`.

## Error Handling

Expected user errors should be handled without tracebacks.

Presenters translate documented Query Layer failures into concise user-facing state while preserving canonical diagnostic meaning.

A failure belongs only to the originating workspace and does not invalidate ready comparison members.

Unexpected exceptions must not be silently swallowed.

## Responsiveness

Run initial queries synchronously.

Do not introduce threading, asynchronous infrastructure, or debounce unless measured operations make the interface noticeably unresponsive.

Even synchronous implementations must enforce workspace-identity and revision-based result acceptance so later execution optimization does not change semantics.

## Validation Strategy

Desktop milestones should include:

- focused tests for pure formatting;
- workspace identity tests;
- independent workspace lifecycle and revision tests;
- duplication-isolation tests;
- presenter tests;
- stale-result and misaddressed-result rejection tests;
- current-versus-retained comparison readiness tests;
- deterministic left/right comparison tests;
- shared Query Layer ownership tests;
- manual interaction checks supplied to the Project Owner;
- architectural import-boundary review;
- full backend regression commands.

Terminal commands must use:

```text
python -m scripts...
```

The Project Owner performs local runtime verification. QA performs static certification and does not claim runtime execution.

## Non-Goals

The current architecture does not approve:

- web services;
- network APIs;
- plugin systems;
- dependency-injection containers;
- global event buses;
- background-worker frameworks;
- persistence databases;
- multi-target planning;
- combined multi-base aggregation;
- asynchronous comparison execution;
- recommendation or ranking engines;
- historical retained-result comparison;
- arbitrary N-way comparison metrics;
- combat simulation;
- stochastic map simulation;
- AI simulation.

## Architectural Review Questions

1. Does the desktop use only the Query Layer and documented public contracts?
2. Is semantic planning state independent of widgets?
3. Are selection revisions and accepted-result revisions explicit?
4. Can an old completion replace newer state?
5. Are presentation and backend behavior separated?
6. Can a second workspace be added without planner redesign?
7. Has unnecessary framework complexity been avoided?
8. Did documentation change where architectural intent changed?
9. Are workspace identity and revision both used to correlate results?
10. Does one workspace's pending or failure state leave every other workspace unchanged?
11. Does comparison consume accepted snapshots rather than constructing another planner?
12. Are retained previous results excluded from current comparison readiness?
13. Is one Query Layer service shared across all workspaces?
14. Do existing single-workspace and single-scenario flows remain compatible?

## Success Criteria

This architecture succeeds when the application can replan automatically from semantic selection changes, stale results cannot become current, the planner remains deterministic and UI-independent, the Query Layer remains authoritative, and multiple isolated workspaces can be compared without replacing the core Planning Workspace lifecycle.

## Interactive Build Plan Timeline (UI-008)

The presenter projects accepted `BuildPlan.steps` into immutable timeline presentation values. The passive view renders a focusable chronological Treeview and independently suppresses equivalent timeline rebuilds. Retained timelines are explicitly labeled as previous.
