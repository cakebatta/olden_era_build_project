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
- side-by-side scenario comparison workspaces;
- immutable multi-objective town planning;
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
- objective-planning modules — immutable objective contracts, objective-set validation, dependency union, provenance, typed failures, and objective completion reporting.
- `scenario.py` — immutable hypothetical starting-state contracts.
- economy and diagnostic modules — deterministic analysis and canonical failure information.
- `query.py` — stable application-facing backend boundary.
- `localization.py` — existing localization-document parsing and duplicate-key validation.
- `planner_localization.py` — planner-scoped display-name indexing and deterministic fallback.

## Application Architecture

The desktop application is a client of the Query Layer.

It must not invoke parser, database, graph, path, localization, objective-planning, or planner-algorithm internals directly.

The interactive product uses application-scoped Planning Workspaces. ARCH-019 defines one workspace lifecycle; ARCH-020 composes independent workspaces in a Scenario Comparison Collection:

```text
Scenario Comparison Collection
    ├── Planning Workspace A ──┐
    ├── Planning Workspace B ──┼── shared Planning Query Service
    └── Planning Workspace N ──┘              ↓
                                      shared planner
```

Each workspace owns its semantic planning selection, result lifecycle, and revision tracking. The collection owns workspace identity, membership, ordering, and comparison selection. Neither layer owns planner algorithms or widget state.

See `docs/planning_workspace_architecture.md`.

See `docs/scenario_comparison_architecture.md`.

## Canonical Boundaries

### Identity

Canonical SIDs, `BuildingKey` values, and typed objective identities are authoritative identifiers.

Localized names are presentation-only and must never become lookup keys.

### Query Layer

The Query Layer coordinates backend capabilities and returns deterministic domain contracts while hiding connected backend state.

Application clients must use documented Query Layer operations. Missing capabilities require an additive Query Layer change rather than a direct import of internals.

One application-scoped `PlanningQueryService` serves every active Planning Workspace. The Query Layer remains unaware of workspace identity, collection membership, display ordering, and comparison presentation.

### Scenario state

`PlanningScenario` is immutable single-town starting-state input. It never mutates canonical parsed data.

The Query Layer resolves effective starting state; the planner remains scenario-independent.

The future aggregate scenario described by the roadmap will own towns and shared economy. It must not be conflated with the existing `PlanningScenario` starting-state contract.

### Multi-objective ownership

The target ownership hierarchy is:

```text
Scenario
    owns Towns

Town
    owns ObjectiveSet

ObjectiveSet
    owns Objective values

TownPlanningRequest
    owns one TownState
    owns one ObjectiveSet

Planner
    consumes TownPlanningRequest

Planner
    returns MultiObjectivePlannerResult
```

For Sprint 18, one town request contains one faction, one starting date, one immutable `PlanningScenario`, and one immutable `ObjectiveSet`.

Future multi-town planning composes multiple town requests under a scenario-level shared-economy scheduler.

### Planning Workspace

The Planning Workspace is application orchestration, not a planner-domain subsystem.

ARCH-022 supersedes the earlier single-target selection rule. Each complete town planning selection owns one immutable `TownPlanningRequest`.

Automatic execution and stale-result handling remain above the Query Layer.

Every workspace owns an independent selection revision, accepted-result revision, pending state, retained-result state, and failure state.

### Multi-objective planning

`Objective` is an explicit closed tagged union of supported immutable objective variants.

The initial supported variant is `BuildingCompletionObjective`. An upgraded building uses the canonical upgraded `BuildingKey`. Future deterministic variants are additive but must define canonical identity, compatibility, completion, provenance, diagnostics, and resource semantics.

One town plan is generated for one immutable `ObjectiveSet`.

The planner solves the union of prerequisite closures for all objectives, removes duplicated graph nodes, applies shared starting-state semantics once, and emits one integrated legal build schedule.

Every scheduled build step exposes reverse objective provenance:

```text
Marketplace
    required_by:
        Treasury
        Resource Silo
```

Single-target planning remains a compatibility case represented by a one-member `ObjectiveSet`.

See `docs/multi_objective_planning_architecture.md`.

### Scenario comparison

Scenario comparison composes independent Planning Workspaces.

Each workspace has stable application identity, independent revisions, and an independent accepted-result lifecycle. No workspace may mutate or invalidate another workspace.

Comparison consumes immutable accepted-result snapshots. It must not:

- create a second planner implementation;
- share mutable workspace lifecycle state;
- treat retained previous results as current;
- reproduce planner or comparison algorithms in presenters;
- infer recommendations or rankings.

The initial detailed comparison selects exactly two current-ready workspaces with explicit left and right roles.

### Planner localization

The existing localization parser retains its current document parsing and
duplicate-key validation semantics.

Planner-facing display names are owned by an immutable
`PlannerLocalizationCatalog`. The catalog indexes only canonical planner-visible
entities from explicit localization sources and applies deterministic fallback:

```text
localized planner name
    ↓ if unavailable
canonical game-data display name
    ↓ if unavailable
canonical identifier
```

The Query Layer owns the catalog and exposes display-ready strings. Presenters
and views never parse localization, read localization paths, or maintain raw
token dictionaries.

See `docs/planner_localization_architecture.md`.

### Presentation

Presenters coordinate application state and Query Layer calls.

Workspace presenters remain partitioned by workspace identity. A comparison presenter consumes immutable collection and accepted-result snapshots.

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
11. Scenario comparison composes isolated workspaces over one authoritative planner.
12. Workspace identity and selection revision jointly determine result ownership.
13. Comparison operates on current accepted results rather than live controls or retained historical output.
14. Planner localization is an immutable Query Layer dependency, not canonical identity.
15. Existing localization-parser duplicate validation remains unchanged.
16. Planner localization indexes explicit planner entities rather than scanning unrelated interface resources.
17. `Objective` is a typed planning-domain union, not an alias for `BuildingKey`.
18. A planner consumes one immutable `TownPlanningRequest` that owns one `ObjectiveSet`.
19. Shared prerequisites appear once in one integrated dependency graph and schedule.
20. Every build step preserves reverse objective provenance.
21. Validation and infeasibility use explicit typed contracts.
22. Single-target planning is preserved as a one-objective compatibility adapter.
23. Future multi-town planning composes town-owned objective sets under a scenario scheduler rather than embedding shared-economy state in the single-town planner.

## Primary Documentation

- `docs/query_layer.md`
- `docs/desktop_application_architecture.md`
- `docs/scenario_planning_architecture.md`
- `docs/planning_workspace_architecture.md`
- `docs/scenario_comparison_architecture.md`
- `docs/planner_localization_architecture.md`
- `docs/multi_objective_planning_architecture.md`
- `docs/project_management_principles.md`
- `docs/team_handoff_protocol.md`
