# Interactive Build Plan Explanation Architecture

## Status

**Decision:** Approved  
**Work item:** ARCH-023 — Interactive Build Plan Explanation Architecture  
**Sprint:** 18 — Planner Experience and Multi-Objective Planning  
**Depends on:** BE-016  
**Production behavior changed by this document:** None  
**Implementation authorized by this document:** No

## Repository Synchronization and Verification

ARCH-023 was designed against the current GitHub `main` documentation and accepted implementation baseline.

The authoritative repository establishes that:

- Sprint 18 is the current Planner Experience and Multi-Objective Planning milestone;
- ARCH-022 is the accepted multi-objective planning architecture;
- BE-015 implements immutable multi-objective planner-domain contracts and integrated planning;
- BE-016 implements immutable Query Layer explanation models and `generate_objective_plan_view(...)`;
- the Query Layer remains the only supported application-facing backend boundary;
- Planning Workspace lifecycle, revision tracking, stale-result rejection, and retained-result semantics remain authoritative;
- views remain passive and interaction mechanisms must not become domain concepts;
- no accepted presentation architecture already defines interactive build-step explanation lifecycle or selection semantics.

No newer repository document supersedes ARCH-023.

No conflict blocks this work.

One implementation constraint requires explicit preservation:

`BuildStepExplanation.resource_balance_before` and
`BuildStepExplanation.resource_balance_after` represent remaining integrated
construction cost, not player inventory or a scenario resource ledger. The
presentation architecture must label these values accordingly and must not infer
inventory semantics.

## Purpose

Define how a user inspects why a planner selected and scheduled a particular
build step while preserving:

- passive views;
- immutable Query Layer contracts;
- deterministic planning;
- Planning Workspace revision ownership;
- localization ownership;
- interaction independence;
- future multi-town compatibility.

ARCH-023 owns presentation architecture only. It does not define visual styling,
widgets, backend algorithms, Query Layer changes, persistence, or planner
behavior.

## Architectural Decision

Add an explanation-presentation subsystem inside each Planning Workspace entry.

Conceptual flow:

```text
User intent to inspect a plan step
        ↓
Passive View emits semantic BuildStepSelectionCommand
        ↓
Workspace Presenter validates current accepted result and revision
        ↓
Presenter selects immutable BuildStepIdentity
        ↓
Presenter obtains immutable explanation data from the accepted
MultiObjectivePlanningResultView or requests the approved Query Layer projection
        ↓
Presenter publishes immutable BuildPlanExplanationPresentation
        ↓
Passive View renders the presentation model
```

The presenter owns selection and explanation-panel lifecycle.

The Query Layer owns explanation facts.

The view owns controls, focus, layout, and interaction mechanics.

The planner remains unaware of selection and explanation presentation.

## Ownership

```text
Desktop Application
    owns PlanningQueryService
    owns PlanningWorkspace
    owns WorkspacePresenter

PlanningWorkspace
    owns one or more BasePlanningState entries

BasePlanningState
    owns current planning request
    owns selection revision
    owns accepted planning result and result revision
    owns planning lifecycle status

WorkspacePresenter
    owns transient explanation selection per BasePlanId
    owns explanation panel lifecycle
    requests or reads immutable Query Layer explanation models
    publishes immutable presentation models

Query Layer
    owns canonical and localized explanation facts
    owns immutable BuildStepExplanation models
    owns immutable ObjectiveCompletionView models
    owns immutable ObjectivePlanningSummary models

View
    owns widgets
    owns focus and navigation mechanics
    reports semantic user intent
    renders immutable presentation models
```

Neither `PlanningWorkspace` nor `BasePlanningState` owns widget identity, focus,
scroll position, or visual expansion state.

Explanation selection is transient application presentation state and is not
canonical scenario data.

## Existing BE-016 Contracts

ARCH-023 consumes the accepted immutable Query Layer models:

```text
ObjectiveSummary
PrerequisiteProvenance
ObjectiveCompletionView
BuildStepExplanation
ObjectivePlanningSummary
MultiObjectivePlanningResultView
```

Canonical operation:

```python
generate_objective_plan_view(
    request: TownPlanningRequest
) -> MultiObjectivePlanningResultView | ObjectivePlanningFailure
```

ARCH-023 does not add or alter Query Layer APIs.

The presenter must not:

- traverse dependency graphs;
- calculate prerequisites;
- infer supporting objectives;
- calculate completion timing;
- calculate downstream unlocks;
- calculate income changes;
- reconstruct localization;
- reinterpret planner diagnostics;
- derive player inventory from remaining construction-cost fields.

## Build-Step Identity

Selection must use semantic plan-step identity, never widget identity.

Conceptual contract:

```python
@dataclass(frozen=True, slots=True)
class BuildStepIdentity:
    base_plan_id: BasePlanId
    result_revision: int
    step_number: int
    building: BuildingKey
```

The combination of `base_plan_id`, `result_revision`, `step_number`, and
canonical building identity binds selection to one accepted result snapshot.

`step_number` alone is insufficient because a later plan may reuse the same
position for a different building.

`BuildingKey` alone is insufficient because future plans may contain repeated
actions of a broader objective type or multiple town contexts.

A future multi-town architecture may replace or extend `base_plan_id` with
canonical `TownId`. The semantic pattern remains unchanged.

## Selection Semantics

Selecting a build step means:

> Inspect the immutable explanation for this step in this accepted result.

It does not mean:

- modify the planner;
- prioritize the step;
- reorder the build plan;
- alter an Objective Set;
- pin the step across unrelated results;
- select a widget.

Only one primary explanation selection is required per workspace entry for the
initial architecture.

Future comparison or multi-selection features may introduce separate typed
selection collections. They must not overload the primary selection contract.

## Interaction Independence

Views report semantic commands such as:

```text
select_build_step(base_plan_id, result_revision, step_number, building)
clear_build_step_selection(base_plan_id)
move_explanation_selection(base_plan_id, direction)
activate_selected_build_step(base_plan_id)
```

The initial implementation may use mouse clicks.

The same presenter contract must support:

- keyboard navigation;
- touch activation;
- search-driven selection;
- timeline-driven selection;
- accessibility actions;
- future cross-view synchronization.

Control-specific events remain view concerns.

## Explanation Panel State

Conceptual presenter-owned lifecycle:

```text
CLOSED
EMPTY
LOADING
READY
FAILED
RETAINED_PREVIOUS_RESULT
```

`LOADING` is permitted only when explanation projection is not already available
with the accepted result or when future asynchronous retrieval is introduced.

The initial BE-016 result view contains all build-step explanations, so normal
selection may transition directly from `EMPTY` or `READY` to `READY` without a
separate backend request.

The architecture retains `LOADING` as a presentation state so future remote,
deferred, or more expensive explanation sources do not require redesign.

### CLOSED

The explanation surface is not active or visible.

No selected build step is required.

### EMPTY

The surface is active, but no current build step is selected.

The presentation model may provide neutral instructional text.

### READY

A selected identity matches the current accepted result and has one immutable
`BuildStepExplanation`.

### FAILED

The current explanation request or projection failed independently of the
planning result.

The failure is presented without planner reasoning or inferred recovery advice.

### RETAINED_PREVIOUS_RESULT

The workspace is pending or failed for a newer planning revision while still
displaying an older accepted result.

An explanation may remain visible only when it is explicitly identified as
belonging to the retained previous result.

It must never be presented as current for the new planning request.

## Immutable Presentation Model

The presenter publishes an immutable model conceptually similar to:

```python
@dataclass(frozen=True, slots=True)
class BuildPlanExplanationPresentation:
    base_plan_id: BasePlanId
    result_revision: int | None
    status: ExplanationPanelStatus
    selected_step: BuildStepIdentity | None
    heading: str
    building_name: str | None
    construction_timing: str | None
    construction_cost: ResourceCost | None
    prerequisite_buildings: tuple[BuildingReferencePresentation, ...]
    supporting_objectives: tuple[ObjectiveReferencePresentation, ...]
    completed_objectives: tuple[ObjectiveReferencePresentation, ...]
    downstream_unlocks: tuple[BuildingReferencePresentation, ...]
    remaining_construction_before: ResourceCost | None
    remaining_construction_after: ResourceCost | None
    income_change: ResourceCost | None
    relevant_diagnostics: tuple[DiagnosticPresentation, ...]
    is_current_result: bool
    message: str | None
```

This is a presentation contract, not a backend domain contract.

The presenter may:

- format dates and resource values;
- choose user-facing labels;
- group immutable facts;
- filter diagnostics by canonical step attribution when the Query Layer already
  provides sufficient attribution;
- produce empty-state and lifecycle messages.

The presenter must not calculate missing explanation facts.

## Explanation Content Semantics

A selected step conceptually exposes:

- localized building name;
- canonical building identity where useful for advanced or fallback display;
- construction day or date;
- construction cost;
- direct prerequisite buildings included by BE-016;
- supporting objectives from `required_by_objectives`;
- objectives directly completed by the step from `objective_targets`;
- directly enabled downstream plan buildings;
- remaining integrated construction requirement before the action;
- remaining integrated construction requirement after the action;
- canonical income change;
- planner diagnostics relevant to the step when explicit attribution exists.

The phrase “resource balance” must not be shown in a way that implies player
inventory unless a future Query Layer contract actually supplies inventory.

Recommended semantic labels are:

```text
Remaining construction requirement before
Remaining construction requirement after
```

## Presenter Responsibilities

The Workspace Presenter:

- owns one transient explanation selection per workspace entry;
- accepts semantic selection commands;
- validates selection against the current or explicitly retained result;
- obtains immutable explanation models only through the Query Layer boundary;
- maps canonical and localized facts into immutable presentation models;
- coordinates explanation state with planning lifecycle updates;
- rejects stale explanation completions using result revision;
- clears invalid selections deterministically;
- distinguishes current and retained previous explanations;
- exposes accessible ordering and selection metadata to the view;
- preserves base or future town attribution.

The presenter does not:

- modify planning requests in response to explanation selection;
- perform graph traversal;
- infer prerequisites or objective provenance;
- calculate resource effects;
- reschedule plans;
- create optimization rationale;
- parse localization;
- use widget identity as selection identity.

## View Responsibilities

Views:

- render immutable explanation presentation models;
- emit semantic selection and navigation intent;
- own visual layout, widgets, focus, scrolling, pointer behavior, touch behavior,
  and keyboard bindings;
- expose appropriate accessible names, roles, states, and relationships;
- indicate current, pending, failed, and retained-result status;
- preserve visible focus during keyboard navigation where practical.

Views do not:

- call planner internals;
- inspect graphs;
- calculate explanation content;
- decide stale-result validity;
- mutate Objective Sets from explanation selection;
- infer why a step exists;
- retain canonical explanation state independently of the presenter.

## Automatic Replanning Semantics

Explanation state must follow deterministic transitions tied to workspace and
result revisions.

### Objectives or planning inputs change

1. The Planning Selection changes.
2. `selection_revision` increments.
3. The accepted result becomes retained previous data or is cleared according to
   existing workspace policy.
4. The existing explanation selection is no longer current.
5. If the retained result remains visible, its explanation may remain visible
   only as `RETAINED_PREVIOUS_RESULT`.
6. The presenter must not silently bind the old selection to a new plan.

### New planning result is accepted

The presenter evaluates the prior selected canonical building against the new
accepted result.

Default rule:

- if the exact selected `BuildingKey` occurs exactly once in the new plan, the
  presenter may deterministically reselect that step using the new
  `result_revision`;
- otherwise selection clears to `EMPTY`.

This preserves user context without relying on old step numbers.

The presenter must not carry selection by list index.

### Selected step disappears

Selection clears to `EMPTY`.

The presentation may state that the previously selected step is not present in
the current plan.

### Scheduling changes but the building remains

The presenter rebinds to the new step identity by canonical building match and
renders the new timing, cost context, and explanation.

Old timing must not remain visible.

### Planning failure occurs

If no accepted result is retained:

- explanation selection clears;
- panel status becomes `EMPTY` or a planning-failure-aware neutral state;
- the explanation panel does not synthesize a step explanation from diagnostics.

If a prior accepted result is retained:

- its explanation may remain visible as `RETAINED_PREVIOUS_RESULT`;
- the current planning failure is visibly separate from the retained
  explanation.

### Incomplete selection

When the Planning Workspace is `EMPTY` or `INCOMPLETE`, no current explanation
selection exists.

### Stale planning completion

A stale planner result is discarded by existing workspace revision rules.

It cannot update explanation selection or presentation.

### Stale explanation completion

If future explanation retrieval becomes asynchronous, a completion is accepted
only when both its captured `base_plan_id` and `result_revision` match the
current explanation request.

## Error Presentation

Three error categories remain distinct.

### Planning request validation or infeasibility

Owned by the planning workspace lifecycle.

The explanation surface does not convert a failed plan into an explanation.

### Explanation projection failure

Owned by explanation panel lifecycle.

The presenter publishes `FAILED` with a stable user-facing message and preserves
canonical error information for logging or diagnostics according to existing
application conventions.

### Presentation formatting failure

A programming defect.

It must not be silently converted into planner diagnostics.

Views must not expose raw stack traces.

## Loading Behavior

BE-016 currently returns explanation models with the accepted plan view, so
selection normally requires no loading state.

A future implementation may retrieve explanations lazily.

If so:

- the accepted build plan remains visible;
- selection intent remains visible;
- the panel becomes `LOADING`;
- the previous explanation may be retained only if clearly marked;
- stale completion checks use `result_revision`;
- loading must not mutate planning state;
- repeated selection of the same current identity may reuse an immutable cached
  model owned by application orchestration, not the view.

## Diagnostics

Only diagnostics explicitly attributable to the selected step should appear as
step-relevant diagnostics.

If BE-016 or another accepted Query Layer contract does not provide enough
canonical attribution, the presenter must show general plan diagnostics
separately rather than infer relevance.

Presenter filtering is limited to matching explicit canonical attribution. It
must not reinterpret severity, cause, or planner reasoning.

## Accessibility Architecture

Accessibility is a view implementation responsibility supported by presenter
semantics.

The architecture requires:

- every selectable step has an accessible name including localized building
  name and plan position or construction timing;
- selection state is programmatically exposed;
- keyboard users can move among selectable plan steps and activate explanation
  without pointer input;
- focus does not depend on visual-only styling;
- panel updates are announced appropriately without excessive interruption;
- current versus retained-result status is conveyed non-visually;
- error and loading states are exposed through accessible status semantics;
- explanation relationships can be understood without relying only on color,
  indentation, hover, or spatial position;
- touch targets and gesture alternatives remain view concerns;
- search-driven selection can target semantic building identity.

The presenter supplies immutable labels, ordering, selection state, and status.
The view maps them to platform accessibility APIs.

## Cross-View Synchronization

Selection is modeled independently of a particular build-plan control.

Future coordinated views may send or observe the same semantic selection:

```text
Build-plan list
Timeline
Objective completion view
Search results
Economy view
Comparison view
```

One presentation selection coordinator may later own synchronized selection for a
town or scenario.

ARCH-023 does not require a global event bus.

Initial implementation should keep selection within the owning Workspace
Presenter and expose explicit commands or callbacks.

## Future Multi-Town Compatibility

The selection contract preserves owner identity:

```text
Scenario
└── Town / BasePlanId
    └── accepted result revision
        └── BuildStepIdentity
```

Future multi-town explanations add canonical `TownId` and shared-economy facts
without changing the core interaction pattern.

A multi-town explanation may additionally expose:

- town identity and localized town label;
- shared-resource contention;
- cross-town prerequisite or timing relationships;
- aggregate income effects;
- scenario-level completion effects.

These facts must come from future immutable Query Layer contracts.

The presenter must not infer cross-town reasoning from independent town views.

## Future Objective Filtering

Filtering affects presentation visibility, not planner intent.

An objective filter may restrict which provenance relationships are displayed.

It must not:

- alter the Objective Set;
- reschedule the plan;
- change completion facts;
- hide the existence of shared prerequisites in canonical result data.

Filter state is transient presenter or view state unless separately approved for
persistence.

## Future Explanation Comparison

Comparison requires an explicit immutable comparison presentation contract.

It may compare:

- the same building across accepted results;
- different selected steps;
- objective support;
- timing;
- costs;
- remaining construction requirements;
- income changes;
- diagnostics.

It must preserve left/right result identity and must not merge facts from
different accepted results.

## Future Optimization Explanations

Optimization rationale is not equivalent to prerequisite explanation.

Future optimizer explanations require backend-owned immutable facts such as:

- objective function;
- considered alternatives;
- constraint effects;
- deterministic tie-break decisions;
- rejected alternatives.

Presenters may format those facts but must not invent optimizer reasoning.

## Persistence

Explanation selection, panel open state, focus, scroll position, loading state,
and retained presentation models are transient.

ARCH-023 does not authorize persistence changes.

A future product decision may persist a semantic selected building or panel
preference, but never widget identity or stale result revision.

## Compatibility

ARCH-023 is additive.

It preserves:

- current planner behavior;
- ARCH-022 objective semantics;
- BE-015 result contracts;
- BE-016 Query Layer explanation contracts;
- existing single-target compatibility;
- Planning Workspace revision and retained-result behavior;
- passive views;
- localization ownership;
- scenario persistence boundaries;
- comparison boundaries;
- deterministic output.

## Explicitly Out of Scope

ARCH-023 does not authorize:

- UI controls;
- layout;
- widgets;
- styling;
- persistence changes;
- planner changes;
- Query Layer changes;
- BE-016 model changes;
- objective filtering implementation;
- timeline synchronization implementation;
- explanation comparison implementation;
- optimizer explanation implementation;
- multi-town planning;
- multi-town explanation facts;
- a global event bus;
- asynchronous infrastructure.

## Validation Requirements

Future UI implementation must validate:

- selection uses semantic step identity rather than widget identity;
- presenter owns selection state;
- views remain passive;
- explanation data comes only from accepted Query Layer contracts;
- no graph or planner reasoning occurs in presentation;
- current and retained-result explanations are distinguishable;
- objective changes invalidate current explanation deterministically;
- accepted result replacement uses canonical building rebinding, never index;
- disappearing steps clear selection;
- scheduling changes update the selected explanation;
- planning failures cannot create synthetic step explanations;
- stale planning and explanation completions are rejected;
- remaining construction-cost fields are not presented as player inventory;
- keyboard-only selection and inspection are possible;
- accessible selection and status are exposed;
- mouse, keyboard, touch, search, and timeline interaction can share the same
  semantic command model;
- future TownId attribution fits without redesign.

## Acceptance

ARCH-023 is complete when documentation establishes:

- explicit explanation-presentation ownership;
- semantic build-step selection;
- immutable presentation models;
- passive view behavior;
- Query Layer-only explanation facts;
- deterministic automatic-replanning transitions;
- error and loading lifecycle;
- accessibility architecture;
- future multi-town, filtering, synchronization, comparison, and optimization
  seams without planner or presenter reasoning.
