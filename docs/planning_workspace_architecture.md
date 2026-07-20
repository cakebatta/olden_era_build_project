# Planning Workspace Architecture

## Status

**Decision:** Approved  
**Work item:** ARCH-019 — Interactive Planning Workspace  
**Scope:** Application architecture for continuous, interaction-independent planning  
**Production behavior changed by this document:** None

## Purpose

This document defines the canonical architecture for the interactive Planning Workspace.

The application is evolving from a transactional workflow, in which the player explicitly requests plan generation, to a responsive workspace in which semantic planning changes automatically refresh planning results, costs, schedules, and diagnostics.

This architecture preserves the deterministic planner, the Query Layer as the supported backend boundary, and separation between application state, presentation, and UI controls.

## Decision

Adopt an application-scoped `PlanningWorkspace` above the Query Layer.

The workspace owns semantic planning selections, planning-result lifecycle, revision tracking, and future per-base planning entries. It does not own planner algorithms, graph traversal, diagnostics generation, presentation formatting, or widget state.

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
PlannerResult or documented failure
    ↓
Workspace result state
    ↓
Presenter
    ↓
View
```

## Architectural Principles

### Player intent, not controls

The application models semantic planning intent.

Checkboxes are the preferred initial UI mechanism, but checkbox state is not a backend or domain contract. The same planning selection may later be produced through drag-and-drop, search, menus, dependency-tree interaction, or workspace restoration.

Canonical building identifiers remain authoritative. Localized labels remain presentation-only.

### Additive evolution

The Planning Workspace is an application orchestration layer. It does not replace or redesign the planner.

Existing Query Layer operations remain compatible. New Query Layer operations require separate architectural approval when their semantics are not already covered by the current public contract.

### Deterministic planning

For identical canonical game data and immutable planning inputs, the planner result must remain identical.

Execution timing, debounce configuration, UI event frequency, thread scheduling, and interaction mechanism must not affect planning semantics.

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

`PlanningSelection` is an immutable application contract representing player intent.

For the initial Sprint 13 implementation, one planning selection contains exactly one requested target and the existing planning inputs required to generate its result:

```text
PlanningSelection
    faction
    target BuildingKey
    starting date
    PlanningScenario
```

The target must use canonical identity.

The initial implementation must not introduce multi-target planning behavior, selected-building collections with undefined semantics, or UI-control concepts.

The architecture reserves the ability to evolve planning selection semantics later. Before arbitrary multiple targets are supported, Architecture and Backend Engineering must define whether the canonical result is a combined dependency plan, independent plans, or a constrained ordered plan.

## Base Planning State

Each workspace entry has stable application identity independent of faction or target.

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

Recommended orchestration statuses are:

```text
EMPTY
INCOMPLETE
PENDING
READY
FAILED
```

These are application lifecycle states, not planner-domain states.

The initial implementation may expose only one base entry. The model must not encode a special one-base or two-base planner.

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

## Update Flow

```text
1. Player changes a planning selection.
2. The view reports a semantic selection command.
3. The presenter or workspace controller applies the command.
4. The workspace creates a new immutable PlanningSelection.
5. The selection revision increments.
6. The entry becomes INCOMPLETE or PENDING.
7. The execution coordinator captures the selection and revision.
8. The coordinator invokes the PlanningQueryService.
9. The Query Layer validates canonical inputs and executes the existing pipeline.
10. PlannerResult or a documented failure returns.
11. The coordinator compares the completion revision with the current revision.
12. A matching completion is accepted; an older completion is discarded.
13. The presenter receives an updated immutable workspace snapshot.
14. The view renders the supplied presentation model.
```

Views should report semantic operations such as:

- set faction;
- set target;
- set starting date;
- replace planning scenario;
- reset planning selection;
- add or remove a base when that feature is enabled.

Views must not report backend implementation operations such as graph traversal or planner invocation.

## Execution Strategy

### Initial implementation

Use:

- synchronous Query Layer calls;
- immediate execution for discrete semantic edits;
- explicit batching for compound replacement operations;
- revision checks even when execution is synchronous;
- logical cancellation through stale-result rejection;
- no planner-level cancellation;
- no general event bus;
- no background worker framework.

### Future optimization

Only after measured responsiveness requires it, the execution coordinator may add:

- a short debounce;
- background execution;
- cooperative cancellation or queued-work replacement.

These changes must remain outside `PlanningSelection`, planner algorithms, and deterministic result semantics.

## Multi-Base Readiness

The workspace is an ordered collection of independent base entries:

```text
PlanningWorkspace
    base_plans: tuple[BasePlanningState, ...]
```

Each entry has a stable `BasePlanId`, allowing multiple bases of the same faction to remain distinct.

The initial product may expose one base, then two, and later up to five. Increasing the supported count must not require planner redesign.

Each base independently owns:

- faction;
- target;
- starting date;
- planning scenario;
- result;
- diagnostics;
- execution status.

Future combined resource information must be produced by a separate deterministic aggregation boundary over accepted per-base results. Combined summaries must preserve per-base attribution and must not replace per-base results.

## Architectural Boundaries

### Planner and graph

The planner and graph remain unaware of:

- workspaces;
- revisions;
- UI interaction;
- execution scheduling;
- multi-base coordination.

They continue to perform deterministic domain behavior.

### Query Layer

The Query Layer remains the only supported application-facing backend boundary.

Continuous execution is an application concern. Query Layer methods remain stateless and deterministic for immutable inputs.

`generate_build_plan(...)` remains compatible. `generate_planner_result(...)`, where present in production code, is the preferred operation when canonical diagnostics and result state are required together.

Arbitrary multi-target planning and workspace-level aggregation require separately approved additive contracts.

### Presenter

Presenters:

- translate view actions into semantic selection commands;
- coordinate workspace mutation and execution;
- render pending, ready, failed, and retained-previous-result states;
- adapt canonical diagnostics without rewriting them;
- associate every result with the correct base and revision.

Presenters must not calculate prerequisites, legality, costs, or scenario state.

### View

Views own:

- widgets;
- accessibility;
- focus and interaction mechanics;
- visual layout;
- visual pending and stale indicators.

Views do not own canonical planning selection, revision validity, planner invocation rules, or backend semantics.

### Persistence

Scenario persistence and active workspace orchestration are distinct responsibilities.

Persistable workspace information may later include base ordering, selections, scenarios, and starting dates.

Pending state, in-flight requests, revision counters, stale completions, and temporary focus are transient and must not be persisted as canonical scenario state.

## Compatibility

This decision is additive.

Existing transactional Query Layer callers remain valid. Existing planner and scenario behavior remains unchanged. An empty scenario remains equivalent to canonical planning.

The Generate action may remain temporarily as a compatibility or fallback path during migration, but ordinary planning edits should no longer require it once interactive planning is implemented.

## Non-Goals

This architecture does not approve:

- multi-target planning;
- multi-base UI behavior;
- combined resource aggregation;
- asynchronous execution;
- debouncing;
- planner optimization;
- drag-and-drop;
- a reactive framework or global event bus;
- planner or graph redesign.

## Required Validation

Implementation must validate:

- immutable semantic selection behavior;
- workspace lifecycle;
- revision increments;
- stale-result rejection;
- Query Layer integration;
- deterministic equivalence for identical selections;
- compatibility of existing planning APIs;
- absence of UI-specific concepts in backend contracts;
- absence of direct desktop imports from planner or graph internals.

## Migration Sequence

1. Introduce the single-base Planning Workspace foundation.
2. Move active target, scenario, and result lifecycle into workspace state.
3. Replace Generate-button-centric orchestration with semantic selection commands.
4. Add persistent summary presentation with explicit pending, current, retained, and failed states.
5. Generalize the workspace collection and enable two bases.
6. Add deterministic combined aggregation through a separately approved contract.
7. Optimize scheduling only after profiling.

## Decision Consequences

### Benefits

- Player interaction becomes responsive rather than transactional.
- UI mechanisms remain replaceable.
- Planner determinism and Query Layer authority are preserved.
- Stale results cannot silently replace newer planning state.
- One-, two-, and five-base workflows share one model.
- Concurrency can be added later without changing planning semantics.

### Costs and risks

- Application state becomes richer than the original transactional desktop state.
- Presenters must explicitly represent pending and retained-result conditions.
- The distinction between current selection and previous accepted result must remain visible.
- Multi-target semantics remain intentionally unresolved and require future approval.
