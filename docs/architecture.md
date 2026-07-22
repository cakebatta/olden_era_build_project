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
- interactive build-plan explanation;
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

## Application Architecture

The desktop application is a client of the Query Layer.

It must not invoke parser, database, graph, path, localization,
objective-planning, or planner-algorithm internals directly.

The Scenario Planning Workspace coordinates planning, explanation, economy,
timeline, and comparison presentation around immutable accepted results.

### Interactive build-plan explanation

BE-016 supplies immutable Query Layer explanation models.

ARCH-023 defines presenter-owned semantic build-step selection and explanation
panel lifecycle.

Canonical flow:

```text
semantic build-step selection
    ↓
Workspace Presenter
    ↓
accepted immutable Query Layer explanation model
    ↓
immutable presentation model
    ↓
passive View
```

The presenter owns transient selection and automatic-replanning reconciliation.

The Query Layer owns explanation facts, localization, objective completion,
prerequisite provenance, downstream plan relationships, income changes, and
remaining integrated construction requirements.

Views own controls, focus, accessibility implementation, and rendering.

No presentation layer may traverse planner graphs or infer planner reasoning.

A build-step selection is bound to owner identity and accepted result revision.
It never changes Objective Set membership, planner priority, or execution order.

See `docs/build_plan_explanation_architecture.md`.

## Canonical Boundaries

### Query Layer

The Query Layer remains the only supported application-facing backend boundary.

Application clients consume immutable explanation models through accepted BE-016
operations. Missing facts require an additive Query Layer change rather than
presentation inference.

### Planning Workspace

The workspace owns semantic planning intent, result lifecycle, and revision state.

The presenter owns transient explanation selection and panel lifecycle.

An explanation for a retained previous result must never be represented as
current for a newer planning request.

### Presentation

Presenters coordinate application state and Query Layer calls.

They may format and group immutable explanation facts but never calculate
prerequisites, provenance, costs, unlocks, income, or diagnostics.

Views remain passive and interaction-independent.

## Design Principles

1. Canonical identifiers are authoritative.
2. Localization is presentation-only and Query Layer-owned.
3. Query Layer operations are deterministic for identical canonical inputs.
4. The planner remains independent of UI lifecycle.
5. Player intent and explanation selection are semantic rather than control state.
6. Views remain passive.
7. Presenters own transient selection and lifecycle, not planner reasoning.
8. Build-step selection is revision-bound and stale-safe.
9. Current and retained explanations are explicitly distinguishable.
10. Remaining construction requirements must not be mislabeled as player inventory.
11. Multi-town explanation extends owner identity and immutable facts without redesigning the presenter/view boundary.
12. Future optimization rationale must be backend-owned and must not be invented by presentation.

## Primary Documentation

- `docs/query_layer.md`
- `docs/planning_workspace_architecture.md`
- `docs/multi_objective_planning_architecture.md`
- `docs/build_plan_explanation_architecture.md`
- `docs/scenario_comparison_architecture.md`
- `docs/planner_localization_architecture.md`
- `docs/project_management_principles.md`
- `docs/team_handoff_protocol.md`
