# Planning Workspace Architecture

## Status

**Decision:** Approved  
**Work item:** ARCH-019 — Interactive Planning Workspace  
**Scope:** Application architecture for continuous, interaction-independent planning  
**Production behavior changed by this document:** None

## Purpose

This document defines the canonical architecture for the interactive Planning Workspace.

The application is evolving from a transactional workflow, in which the player explicitly requests plan generation, to a responsive workspace in which semantic planning changes automatically refresh planning results, costs, schedules, diagnostics, and approved explanation presentation.

This architecture preserves the deterministic planner, the Query Layer as the supported backend boundary, and separation between application state, presentation, and UI controls.

## Decision

Adopt an application-scoped `PlanningWorkspace` above the Query Layer.

The workspace owns semantic planning selections, planning-result lifecycle, revision tracking, and future per-base planning entries. It does not own planner algorithms, graph traversal, diagnostics generation, explanation generation, presentation formatting, or widget state.

The canonical flow is:

```text
Interaction mechanism
    ↓
Planning Workspace
    ↓
Planning Execution Coordinator
    ↓
Planning Query Service
    ↓
Planner / graph / scenario pipeline
    ↓
PlannerResult, MultiObjectivePlanningResultView, or documented failure
    ↓
Workspace result state
    ↓
Presenter
    ↓
View
```

ARCH-023 adds a presenter-owned build-step explanation selection and panel lifecycle over accepted immutable Query Layer explanation models.

See `docs/build_plan_explanation_architecture.md`.

## Architectural Principles

### Player intent, not controls

The application models semantic planning intent and semantic explanation selection.

Checkboxes, list rows, timeline markers, and other controls are interaction mechanisms, not backend or application identity.

Canonical building identifiers remain authoritative. Localized labels remain presentation-only.

### Additive evolution

The Planning Workspace is application orchestration. It does not replace or redesign the planner.

Existing Query Layer operations remain compatible. Explanation presentation consumes accepted BE-016 contracts without adding planner reasoning.

### Deterministic planning and explanation lifecycle

For identical canonical game data and immutable planning inputs, planner results remain identical.

For identical workspace status, accepted result revision, and semantic explanation selection, explanation presentation state remains deterministic.

Execution timing, debounce configuration, UI event frequency, thread scheduling, and interaction mechanism must not affect planning or explanation semantics.

## Planning Workspace

A `PlanningWorkspace` is the application-scoped representation of the player's active planning activity.

It contains:

- an ordered collection of base-planning entries;
- the semantic planning selection for each entry;
- the latest planning status and accepted result for each entry;
- revision information used to reject stale completions;
- future workspace-level combined summaries when separately approved.

It does not contain:

- widgets or widget identifiers;
- checkbox variables;
- mouse or keyboard events;
- localized display names as identity;
- graph or planner algorithms;
- explanation derivation;
- formatting strings;
- debounce duration.

The desktop application owns one active workspace for the user session.

Conceptual ownership:

```text
Desktop Application
    owns PlanningQueryService
    owns PlanningWorkspace
    owns PlanningExecutionCoordinator
    owns WorkspacePresenter
```

## Planning Selection

`PlanningSelection` remains an immutable application contract representing player intent.

ARCH-022 supersedes the former single-target limitation. A complete town
selection owns one immutable `TownPlanningRequest`, containing one `TownState`
and one immutable `ObjectiveSet`.

Objective Set order does not specify execution order.

## Base Planning State

Each workspace entry has stable application identity independent of faction or objectives.

Conceptually:

```text
BasePlanningState
    base_id
    selection
    selection_revision
    execution_status
    accepted_result
    result_revision
    latest_failure
```

Recommended orchestration statuses remain:

```text
EMPTY
INCOMPLETE
PENDING
READY
FAILED
```

These are application lifecycle states, not planner-domain states.

Explanation selection is presenter-owned transient state rather than a field of canonical planning input.

## Revision and Result Rules

Every accepted semantic selection mutation increments the entry's `selection_revision`.

An execution captures:

```text
base_id
immutable selection snapshot
selection_revision
```

A completion may update the workspace only when its captured revision equals the current selection revision.

Older completions are stale and must be discarded.

The workspace may retain the last accepted result while a replacement is pending or while the current request has failed. Presentation must clearly distinguish a retained previous result from a result generated for the current selection.

An old result must never be represented as current.

Explanation state follows the accepted result's `result_revision`.

## Update Flow

```text
1. Player changes a planning selection.
2. The view reports a semantic selection command.
3. The presenter or workspace controller applies the command.
4. The workspace creates a new immutable planning request.
5. The selection revision increments.
6. The entry becomes INCOMPLETE or PENDING.
7. The execution coordinator captures the selection and revision.
8. The coordinator invokes the PlanningQueryService.
9. The Query Layer validates canonical inputs and executes the pipeline.
10. Immutable result view or documented failure returns.
11. The coordinator compares the completion revision with the current revision.
12. A matching completion is accepted; an older completion is discarded.
13. The presenter reconciles explanation selection against the accepted result revision.
14. The presenter publishes an updated immutable workspace and explanation presentation.
15. The view renders supplied presentation models.
```

Views should report semantic planning and explanation operations.

Views must not report backend implementation operations such as graph traversal,
planner invocation, or explanation calculation.

## Build-Plan Explanation Relationship

ARCH-023 defines interactive explanation presentation.

The presenter owns:

- selected `BuildStepIdentity`;
- explanation panel state;
- rebinding or clearing selection after replanning;
- current versus retained-result presentation;
- immutable explanation presentation models.

The Query Layer owns explanation facts through BE-016.

The view owns interaction mechanics, accessibility implementation, and rendering.

A selected plan step never changes planning intent or planner order.

## Execution Strategy

Initial execution remains synchronous and revision-aware.

BE-016 normally returns all build-step explanations with the accepted result view,
so selecting a step does not require planner execution.

Future lazy or asynchronous explanation retrieval may be added only outside
planner semantics and with result-revision stale-completion checks.

## Multi-Base and Multi-Town Readiness

The workspace remains an ordered collection of independent base or future town entries.

Each entry preserves stable owner identity and accepted result revision.

Explanation selection includes owner identity, result revision, step number, and
canonical building identity.

Future multi-town shared-economy results may add canonical TownId and
scenario-level explanation facts without changing the presenter/view boundary.

## Architectural Boundaries

### Planner and graph

Remain unaware of workspaces, revisions, interaction, explanation selection, and presentation.

### Query Layer

Remains the only supported application-facing backend boundary.

`generate_objective_plan_view(...)` supplies immutable explanation facts.

### Presenter

Presenters:

- translate view actions into semantic planning and explanation commands;
- coordinate workspace mutation and execution;
- render pending, ready, failed, and retained-previous-result states;
- own explanation selection and panel lifecycle;
- adapt immutable Query Layer facts without rewriting them;
- associate every result and explanation with the correct base and revision.

Presenters must not calculate prerequisites, legality, costs, scenario state,
objective provenance, downstream unlocks, or planner rationale.

### View

Views own:

- widgets;
- accessibility implementation;
- focus and interaction mechanics;
- visual layout;
- visual pending and stale indicators;
- pointer, keyboard, touch, and search interaction.

Views do not own canonical planning selection, revision validity, planner
invocation rules, explanation facts, or backend semantics.

### Persistence

Scenario persistence and active workspace orchestration remain distinct.

Explanation selection, panel state, result revision, temporary focus, and scroll
position are transient and are not persisted by ARCH-023.

## Compatibility

This decision is additive.

Existing transactional Query Layer callers, planner behavior, scenario behavior,
workspace lifecycle, localization, and persistence remain unchanged.

## Non-Goals

This architecture does not approve:

- UI controls or layout;
- multi-town planning;
- explanation persistence;
- planner or graph redesign;
- Query Layer changes;
- optimizer rationale;
- a global event bus.

## Required Validation

Implementation must validate:

- immutable semantic planning and explanation selection;
- workspace lifecycle;
- revision increments;
- stale-result rejection;
- Query Layer integration;
- passive views;
- semantic step identity;
- deterministic explanation reconciliation after replanning;
- retained-result distinction;
- accessibility support;
- absence of planner or graph reasoning in presentation;
- absence of direct desktop imports from planner or graph internals.

## Decision Consequences

### Benefits

- Users can inspect planner decisions without exposing planner internals.
- Explanation interaction remains independent of widgets.
- Automatic replanning cannot silently attach stale explanations to new plans.
- Passive views and Query Layer authority remain intact.
- Multi-town and timeline synchronization can reuse the same semantic selection model.

### Costs and risks

- Presenter state becomes richer.
- Current and retained explanations must remain visibly distinct.
- Canonical result revision must accompany explanation selection.
- BE-016 remaining-construction fields require careful labeling to avoid inventory misrepresentation.

## UI-012 Interactive Build Plan Explanation

The presenter owns semantic BuildStepIdentity selection and accepted-result revision reconciliation. The passive view renders immutable explanation sections and forwards semantic timeline intent. Remaining before/after values are labeled as integrated construction requirements, not inventory.
