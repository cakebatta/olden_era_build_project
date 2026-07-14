# Desktop Application Architecture Specification

## Purpose

This document defines the architectural boundaries for the first desktop application built on top of Query Layer Version 1.0.

The desktop application should make deterministic planning workflows accessible without coupling presentation code to parser, database, graph, localization, path, or planner-algorithm internals.

This specification defines structure and ownership. User-facing workflows are documented separately.

## Architectural Position

```text
Game Assets
    ↓
Backend Parsers and Models
    ↓
Planning and Graph Algorithms
    ↓
Query Layer Version 1.0
    ↓
Desktop Application
```

The desktop application is a client of the Query Layer.

It may use the documented stable domain contracts accepted or returned by the Query Layer, but it must not invoke internal backend modules directly.

## Initial Product Scope

The first desktop milestone is a Build Planner application.

It should allow a user to:

- discover available factions;
- discover buildings for a selected faction;
- discover valid levels for a selected building;
- generate one deterministic build plan;
- inspect direct prerequisites;
- inspect construction steps and dates;
- inspect individual and cumulative resource costs;
- inspect a bounded set of alternative legal build orders.

Future analysis modules must not complicate the initial planner architecture.

## Technology Decision

Use the Python standard-library `tkinter` toolkit for the initial desktop application.

Reasons:

- no new runtime dependency;
- suitable for the current single-window planning workflow;
- consistent with the project's preference for minimal dependencies;
- sufficient for validating application architecture and user workflows.

This decision may be revisited if concrete requirements exceed `tkinter`'s capabilities.

## Application Structure

Preferred package structure:

```text
olden_db/
    desktop/
        __init__.py
        app.py
        state.py
        views/
            __init__.py
            planner_view.py
        presenters/
            __init__.py
            planner_presenter.py
        formatting.py
```

### `app.py`

Owns application startup, root-window creation, `PlanningQueryService` construction, top-level dependency wiring, navigation, and shutdown.

### `state.py`

Owns minimal shared selection state, such as selected faction, building SID, level, starting date, latest plan, and alternative-order limit.

Do not introduce a generic state-management framework.

### `views/`

Owns widget construction, input collection, local widget state, display, and validation messages.

Views must not implement planning rules or query backend internals.

### `presenters/`

Owns coordination between views, application state, and `PlanningQueryService`.

Presenters may call Query Layer methods, translate Query Layer errors, update state, and supply structured results to views.

Use plain Python presenter classes. Do not introduce MVVM frameworks or event-bus abstractions.

### `formatting.py`

Owns pure presentation formatting for stable public domain contracts, including resource costs, game dates, building identities, and plan steps.

## Window and Navigation Model

Use one primary application window.

Preferred layout:

```text
┌──────────────────────────────────────────────────────┐
│ Application title                                    │
├───────────────┬──────────────────────────────────────┤
│ Navigation    │ Active module                        │
│               │                                      │
│ Build Planner │ Planner controls and results         │
│               │                                      │
├───────────────┴──────────────────────────────────────┤
│ Status / validation message                          │
└──────────────────────────────────────────────────────┘
```

For the first milestone, Build Planner may be the only active navigation item.

Use dialogs only for brief errors, confirmations, focused settings, or file selection.

## Planner View Responsibilities

### Target Selection

Controls for faction, building SID, building level, and optional starting date.

Selectors must be populated through Query Layer discovery methods.

Changing an upstream selection should clear invalid downstream state.

### Plan Results

Display target identity, direct prerequisites, construction sequence, dates, individual step costs, cumulative costs, and total cost.

The results region should support scrolling.

### Alternative Orders

Display a bounded number of legal build orders.

The user must choose or accept a finite safe limit.

## State Ownership

Construct one application-scoped `PlanningQueryService` during startup.

Views must not construct their own query services.

Suggested ownership:

```text
Application
    owns Query Service
    owns Application State
    owns Planner Presenter

Planner Presenter
    reads/writes Application State
    calls Query Service
    updates Planner View

Planner View
    owns widgets
    reports user actions
    renders supplied results
```

Prefer explicit callbacks over a global event bus.

## Query Layer Integration

All backend operations must use documented Query Layer Version 1.0 methods.

The desktop application may import stable public domain contracts identified in `docs/query_layer.md`.

It must not import parser, unit parser, database, graph, localization, path, or planner-algorithm internals.

Missing capabilities must be reported rather than bypassed.

## Localization

Canonical SIDs remain the source of identity.

Localized names are supplementary presentation and must never become lookup keys.

If public localization access is insufficient, create a narrowly scoped Query Layer evolution task before implementing the dependent UI feature.

## Error Handling

Expected user errors should be handled without tracebacks.

The presenter should translate Query Layer exceptions into concise user-facing messages.

Unexpected exceptions should not be silently swallowed.

A full logging framework is not required initially.

## Responsiveness

Run initial queries synchronously.

Do not introduce threading or asynchronous infrastructure unless measured operations make the interface noticeably unresponsive.

## Validation Strategy

Desktop milestones should include:

- focused tests for pure formatting functions;
- presenter tests where practical;
- manual interaction checks;
- architectural import-boundary review;
- full backend regression commands.

Terminal commands must use:

```text
python -m scripts...
```

The Project Owner performs local runtime verification.

## Future Module Map

Potential future modules:

- Build Planner
- Strategy Comparison
- Building Browser
- Unit Browser
- Economy Analysis
- Settings
- Help / About

Do not create empty modules solely for anticipated features.

## Non-Goals

The initial architecture does not include web services, network APIs, plugin systems, dependency-injection containers, global event buses, background-worker frameworks, persistence databases, combat simulation, stochastic map simulation, or AI simulation.

## Initial Desktop Milestone Boundary

The first implementation milestone should:

- launch successfully;
- construct the Query Layer through its canonical factory;
- display one root window;
- include a stable navigation region;
- include an empty or minimally wired Build Planner view;
- keep UI files separated according to this specification;
- introduce no backend changes;
- establish clean shutdown.

It should not implement the full planner workflow yet.

## Architectural Review Questions

1. Does the UI use only the Query Layer and documented public contracts?
2. Is presentation separated from backend operations?
3. Is state explicit and narrowly scoped?
4. Can future modules be added without redesigning the root window?
5. Has unnecessary framework complexity been avoided?
6. Can the feature be validated independently?
7. Did documentation change where architectural intent changed?

## Success Criteria

This architecture succeeds if the planner workflow can be implemented without bypassing the Query Layer, future modules can be added without restructuring the root application, backend changes remain isolated behind Version 1.0, and a new UI engineer can identify where each kind of code belongs.
