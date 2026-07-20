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
Planning Workspace and Application Orchestration
    ↓
Desktop Presenters and Views
```

The desktop application is a client of the Query Layer.

It may use documented stable contracts accepted or returned by the Query Layer, but it must not invoke internal backend modules directly.

## Current Product Direction

The primary desktop workflow is an interactive Planning Workspace.

The user should be able to:

- discover factions and buildings;
- select one canonical planning target per active base;
- change hypothetical starting state;
- receive automatic plan and diagnostic updates;
- inspect construction steps, dates, costs, and completion information;
- revise the selection without repeatedly invoking a separate Generate action;
- retain a clearly marked previous summary while a replacement is pending;
- later coordinate multiple independent base plans.

The initial Sprint 13 implementation remains single-base and single-target. Multi-target planning, multi-base UI behavior, and combined resource aggregation require later work.

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
        views/
        presenters/
        formatting.py
```

Exact filenames may evolve, but responsibilities must remain separated.

### Application startup

Owns root-window creation, one application-scoped `PlanningQueryService`, the active `PlanningWorkspace`, execution coordination, top-level dependency wiring, navigation, and shutdown.

### Workspace and state

Own semantic application state:

- active base entries;
- immutable planning selection;
- selection revision;
- execution status;
- latest accepted result;
- current failure;
- transient UI-independent workspace state.

It must not store widgets, localized labels as identity, or planner algorithms.

Do not introduce a generic state-management framework.

### Execution coordination

Owns when Query Layer planning is invoked and whether a completion is still current.

The initial implementation uses synchronous calls and revision-based stale-result protection.

Debounce, background execution, and cooperative cancellation remain deferred until measured responsiveness requires them.

### Views

Own widget construction, accessibility, focus, local interaction mechanics, display, and validation messages.

Views report semantic actions. They must not implement planning rules, result-validity rules, or query backend internals.

### Presenters

Own coordination between views, workspace state, execution coordination, and `PlanningQueryService`.

Presenters may:

- translate UI actions into semantic selection commands;
- apply workspace mutations;
- request execution;
- translate documented Query Layer errors;
- supply immutable presentation models;
- render pending, ready, failed, and retained-previous-result states.

Presenters must not derive prerequisite legality, costs, diagnostics, or effective scenario state.

Use plain Python presenter classes. Do not introduce MVVM frameworks or global event buses.

### Formatting

Owns pure presentation formatting for stable public domain contracts, including resource costs, game dates, building identities, plan steps, diagnostics, and workspace statuses.

## Planning Workspace Ownership

```text
Application
    owns PlanningQueryService
    owns PlanningWorkspace
    owns PlanningExecutionCoordinator
    owns WorkspacePresenter

PlanningWorkspace
    owns semantic selections
    owns revisions
    owns accepted results and current failures

PlanningExecutionCoordinator
    captures immutable selection snapshots
    calls PlanningQueryService
    rejects stale completions

WorkspacePresenter
    handles semantic actions
    renders workspace snapshots

View
    owns widgets
    reports user actions
    renders supplied presentation models
```

Prefer explicit callbacks over a global event bus.

## Planning Selection

For the initial interactive implementation, one base entry contains exactly one requested canonical target plus its starting date and immutable `PlanningScenario`.

The planning model must not contain:

- checkbox variables;
- widget IDs;
- drag coordinates;
- mouse or keyboard events;
- localized names as identity.

Changing interaction mechanisms must not require planner or Query Layer redesign.

## Revision and Result Lifecycle

Every semantic selection mutation increments the base entry's selection revision.

Execution captures the immutable selection and revision.

A completion is accepted only if its revision still matches the current selection. Older completions are discarded.

Recommended statuses:

```text
EMPTY
INCOMPLETE
PENDING
READY
FAILED
```

The latest accepted result may remain visible while a replacement is pending or after the current request fails, but the view must identify it as retained previous information rather than current output.

## Query Layer Integration

All backend operations must use documented Query Layer methods.

The desktop may import documented stable public domain contracts. It must not import parser, unit parser, database, graph, localization, path, or planner-algorithm internals.

Missing capabilities must be reported and addressed through a reviewed Query Layer evolution.

Continuous replanning is an application concern. Query Layer operations remain stateless and deterministic.

## Scenario Integration

Each base entry owns its own immutable `PlanningScenario`.

The Query Layer remains authoritative for effective starting-building state.

A scenario edit creates a new planning selection revision and triggers replanning when the selection is complete.

Scenario state is not inferred from canonical building fields.

## Multi-Base Direction

The workspace is an ordered collection of base entries with stable application identities.

The product may initially expose one base, then two, and later up to five without changing planner algorithms.

Per-base results remain authoritative and distinct.

Future combined resource summaries require a separate deterministic aggregation contract and must preserve base attribution.

## Localization

Canonical identifiers remain the source of identity.

Localized names are supplementary presentation and must never become lookup keys.

## Error Handling

Expected user errors should be handled without tracebacks.

Presenters translate documented Query Layer failures into concise user-facing state while preserving canonical diagnostic meaning.

Unexpected exceptions must not be silently swallowed.

## Responsiveness

Run initial queries synchronously.

Do not introduce threading, asynchronous infrastructure, or debounce unless measured operations make the interface noticeably unresponsive.

Even synchronous implementations must enforce revision-based result acceptance so later execution optimization does not change semantics.

## Validation Strategy

Desktop milestones should include:

- focused tests for pure formatting;
- workspace lifecycle and revision tests;
- presenter tests;
- stale-result rejection tests;
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
- combat simulation;
- stochastic map simulation;
- AI simulation.

## Architectural Review Questions

1. Does the desktop use only the Query Layer and documented public contracts?
2. Is semantic planning state independent of widgets?
3. Are selection revisions and accepted-result revisions explicit?
4. Can an old completion replace newer state?
5. Are presentation and backend behavior separated?
6. Can a second base be added without planner redesign?
7. Has unnecessary framework complexity been avoided?
8. Did documentation change where architectural intent changed?

## Success Criteria

This architecture succeeds when the application can replan automatically from semantic selection changes, stale results cannot become current, the planner remains deterministic and UI-independent, the Query Layer remains authoritative, and the workspace can scale from one base to multiple bases without replacing the core model.
