# Olden Era Build Planner — Architecture

## Purpose

Build a deterministic planning and analysis application for Heroes of Might & Magic: Olden Era tournament play.

The application models:

- building prerequisites;
- resource costs;
- construction timing;
- recruitment and deterministic town-income effects;
- multiple legal build orders;
- hypothetical starting scenarios;
- diagnostics and planning failures;
- interactive planning workspaces;
- localized display names.

It intentionally does not treat random map income or other stochastic map events as canonical planning inputs.

## Architectural Layers

```text
Game Assets
    ↓
Parsers and Canonical Models
    ↓
Dependency Graph, Planner, Economy, and Diagnostic Algorithms
    ↓
Query Layer
    ↓
Application Orchestration
    ↓
Presenters and Formatting
    ↓
Desktop Views
```

## Core Backend Modules

- `models.py` — shared canonical data structures.
- `constants.py` — shared constants.
- `paths.py` — canonical project paths.
- `parser.py` — city and building logic parsing.
- `unit_parser.py` — unit logic parsing.
- `database.py` — connected in-memory game data.
- `graph.py` — dependency graph and legal topological orders.
- `planner.py` — deterministic build plans, dates, and cumulative costs.
- `scenario.py` — immutable hypothetical starting-state contracts.
- economy and diagnostic modules — deterministic analysis and canonical failure information.
- `query.py` — stable application-facing backend boundary.
- `localization.py` — canonical identifier to display-text support.

## Application Architecture

The desktop application is a client of the Query Layer.

It must not invoke parser, database, graph, path, localization, or planner-algorithm internals directly.

The interactive product uses an application-scoped Planning Workspace:

```text
Planning Workspace
    ↓
Planning Execution Coordinator
    ↓
Planning Query Service
    ↓
PlannerResult or documented failure
    ↓
Presenter
    ↓
View
```

The workspace owns semantic planning selection, result lifecycle, and revision tracking. It does not own planner algorithms or widget state.

See `docs/planning_workspace_architecture.md`.

## Canonical Boundaries

### Identity

Canonical SIDs and `BuildingKey` values are authoritative identifiers.

Localized names are presentation-only and must never become lookup keys.

### Query Layer

The Query Layer coordinates backend capabilities and returns deterministic domain contracts while hiding connected backend state.

Application clients must use documented Query Layer operations. Missing capabilities require an additive Query Layer change rather than a direct import of internals.

### Scenario state

`PlanningScenario` is immutable semantic input. It never mutates canonical parsed data.

The Query Layer resolves effective starting state; the planner remains scenario-independent.

### Planning Workspace

The Planning Workspace is application orchestration, not a planner-domain subsystem.

For the initial interactive implementation, each planning selection contains exactly one canonical target. Automatic execution and stale-result handling occur above the Query Layer.

### Presentation

Presenters coordinate application state and Query Layer calls.

Views own widgets and interaction mechanics. Formatting remains pure presentation behavior.

## Design Principles

1. Canonical identifiers are authoritative.
2. Localization is presentation-only.
3. Parsers are reusable and path-agnostic.
4. `paths.py` is the only backend module aware of repository layout.
5. Every behavior change requires executable validation where practical.
6. Query Layer operations are deterministic for identical data and inputs.
7. The planner remains independent of UI lifecycle and scenario-document persistence.
8. Player intent is modeled semantically rather than as checkbox state.
9. Multi-base planning is an N-base workspace, not a special two-base planner.
10. New infrastructure is introduced only for measured or approved needs.

## Primary Documentation

- `docs/query_layer.md`
- `docs/desktop_application_architecture.md`
- `docs/scenario_planning_architecture.md`
- `docs/planning_workspace_architecture.md`
- `docs/project_management_principles.md`
- `docs/team_handoff_protocol.md`
