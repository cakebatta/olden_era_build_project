# Desktop Application User Workflow Specification

## Purpose

This document defines how users interact with the first desktop version of the Olden Era Build Planner.

It complements `docs/desktop_application_architecture.md`.

The architecture specification explains how the application is organized. This document explains what the user does, what the application displays, and how the interface responds.

---

## Primary User Goal

The first desktop application should help a user answer:

> What must I build, in what order, and at what cumulative resource cost to reach a selected building?

The initial experience should prioritize clarity and verification over density or advanced customization.

---

## Primary Workflow

```text
Launch application
    ↓
Select faction
    ↓
Select building
    ↓
Select building level
    ↓
Optionally select starting date
    ↓
Generate plan
    ↓
Review prerequisites
    ↓
Review dated construction steps
    ↓
Review cumulative resource costs
    ↓
Optionally inspect alternative legal build orders
```

The application should guide the user through this sequence without requiring prior knowledge of canonical identifiers.

---

## Application Launch

On launch, the application should:

1. Construct `PlanningQueryService` using the canonical Query Layer factory.
2. Load the list of available factions.
3. Open the main application window.
4. Select the Build Planner module.
5. Display an empty planner state with clear instructions.

The application should not automatically generate a plan before a target is selected.

### Initial Empty-State Message

Recommended meaning:

> Select a faction, building, and level to generate a build plan.

The exact wording is a UI decision, but it should clearly explain the next action.

---

## Faction Selection

The faction selector should be populated through:

```text
PlanningQueryService.list_factions()
```

### Expected Behavior

When the user selects a faction:

- populate the building selector;
- clear any previous building selection;
- clear any previous level selection;
- clear stale prerequisites;
- clear stale plan output;
- clear stale alternative orders;
- reset status messages related to the previous target.

Changing faction invalidates all downstream selections and results.

### Display

The initial version may display canonical faction identifiers.

Localized faction names may be added later through a documented public presentation interface.

Canonical identifiers must remain available for debugging and validation.

---

## Building Selection

The building selector should be populated through:

```text
PlanningQueryService.list_buildings(faction)
```

### Expected Behavior

When the user selects a building:

- populate valid building levels;
- clear any previous level selection;
- clear stale plan results;
- clear stale alternative orders;
- retain the selected faction.

Changing building invalidates all result data dependent on the prior building.

### Search and Filtering

Searchable selection is desirable but not required for the first functional milestone.

A standard dropdown is acceptable initially if the list remains usable.

---

## Level Selection

The level selector should be populated through:

```text
PlanningQueryService.list_building_levels(faction, sid)
```

### Expected Behavior

When the user selects a level:

- the application now has a complete target;
- the Generate Plan action becomes enabled;
- stale results from another level are cleared.

The UI should not allow arbitrary invalid levels where a constrained selector can prevent them.

---

## Starting Date

The initial default starting date should be:

```text
Month 1, Week 1, Day 1
```

The first desktop version may use the default without exposing custom date input.

If custom date selection is included, it should:

- constrain month, week, and day to valid values;
- construct the documented public `GameDate` contract;
- clearly show the resulting date code or human-readable date;
- reset stale plan output when changed.

Custom date input is optional for the first functional planner screen.

---

## Generate Plan Action

The Generate Plan action should remain disabled until faction, building, and level are valid.

When activated, the presenter should request:

```text
get_building(...)
get_prerequisites(...)
generate_build_plan(...)
get_cumulative_cost(...)
```

The application should update the result regions as one coherent user action.

### Successful Result

On success, display:

- selected target;
- direct prerequisites;
- dated construction steps;
- individual cost of each step;
- cumulative cost after each step;
- total cost;
- completion date.

### No Construction Required

If the target is already constructed at game start:

- explain that no construction actions are required;
- still display target details;
- display zero additional cost;
- avoid presenting the empty result as an error.

### Failure

Expected Query Layer errors should be shown as concise user-facing messages without a traceback.

The prior successful result should either remain visible with a clear warning or be cleared consistently. For the first implementation, clearing invalid stale results is preferred.

---

## Prerequisite Display

Direct prerequisites should be displayed separately from the full construction sequence.

This distinction should remain clear:

- Direct prerequisites are immediate requirements.
- The build plan includes the complete prerequisite closure in legal order.

If there are no direct prerequisites, display:

> No direct prerequisites.

Do not leave the area blank in a way that looks like failed loading.

---

## Build Plan Display

Each plan step should show:

- step number;
- construction date;
- building identity;
- individual cost;
- cumulative cost.

Canonical identity should include:

- faction;
- SID;
- level.

Localized names may be shown as supplementary text when available.

### Recommended Reading Order

```text
Step 1
Date
Building
Individual cost
Cumulative cost
```

The results area should be scrollable.

The application should not compress all resource values into an unreadable single line if a structured presentation is clearer.

---

## Resource Cost Display

Resource costs should show only meaningful values by default.

Zero-valued resources may be omitted from compact summaries.

A detailed view may show every resource later, but is not required initially.

The same formatting convention should be used for:

- building cost;
- step cost;
- cumulative step cost;
- total plan cost.

---

## Alternative Legal Build Orders

Alternative orders are a secondary workflow.

They should not distract from the primary deterministic plan.

### Entry Point

Provide an action such as:

```text
Show Alternative Orders
```

The user should specify or accept a finite result limit.

Recommended default:

```text
10
```

Recommended maximum for the initial UI:

```text
100
```

### Expected Behavior

The application should call:

```text
enumerate_build_orders(..., max_orders=limit)
```

It must not request an unbounded result set.

Each order should display:

- order number;
- ordered construction actions;
- canonical building identity for each action.

Alternative-order display may be collapsible, tabbed, or placed beneath the primary plan.

A separate top-level window is not required.

---

## Navigation Workflow

The first release may contain only one functional module:

- Build Planner

The navigation area should still be stable so future modules can be added later.

Selecting Build Planner should preserve the current planning session unless the application explicitly resets it.

Future inactive modules should not appear as misleading functional options.

Do not create nonfunctional menu items solely to advertise future plans.

---

## Status and Feedback

The application should provide a persistent status region or equivalent feedback mechanism.

Examples:

- Ready
- Factions loaded
- Select a building
- Plan generated successfully
- No direct prerequisites
- Request could not be completed

Status messages should supplement the main result, not replace it.

---

## Error and Recovery Workflows

### Invalid Selection State

Where possible, prevent invalid combinations through dependent selectors.

### Query Error

Display a concise message and allow the user to adjust selections.

### Missing Game Assets

If canonical data cannot load during startup:

- display a clear startup failure message;
- explain that required game assets could not be loaded;
- do not open a partially functioning planner;
- avoid exposing a raw traceback to the user.

### Unexpected Error

During development, unexpected errors may be logged for diagnosis.

The user should see a general failure message and retain the ability to close the application cleanly.

---

## State Reset Rules

The application should clear stale dependent state consistently.

### Changing Faction Clears

- building;
- level;
- prerequisites;
- plan;
- total cost;
- alternative orders.

### Changing Building Clears

- level;
- prerequisites;
- plan;
- total cost;
- alternative orders.

### Changing Level Clears

- prerequisites;
- plan;
- total cost;
- alternative orders.

### Changing Starting Date Clears

- plan;
- total cost;
- alternative orders.

The UI should never display results for a target different from the current selectors.

---

## First Functional Milestone

The first functional planner milestone should support:

1. Launching the desktop application.
2. Selecting faction.
3. Selecting building.
4. Selecting level.
5. Generating a deterministic plan.
6. Displaying direct prerequisites.
7. Displaying dated steps.
8. Displaying cumulative costs.
9. Handling expected errors.
10. Cleanly exiting.

Alternative legal build orders may be included in the same milestone only if the core workflow is already stable.

---

## Deferred Workflows

The following are intentionally deferred:

- comparing multiple targets side by side;
- saving favorite plans;
- exporting plans;
- persistent settings;
- strategy scoring;
- randomized economy assumptions;
- map-aware planning;
- combat simulation;
- unit-growth analysis;
- keyboard customization;
- theme selection;
- automatic update checks.

These should not shape the initial implementation unless a concrete requirement emerges.

---

## Manual Acceptance Scenario

Use the following representative workflow:

```text
Launch application
Select faction: nature
Select building SID: Build_Tier_4
Select level: 2
Generate plan
```

Confirm that:

- prerequisites display;
- the deterministic plan displays;
- dates are readable;
- costs are readable;
- canonical identifiers are preserved;
- no traceback appears;
- changing the faction clears the prior result;
- returning to the original target regenerates the same plan.

For alternative orders:

```text
Limit: 10
```

Confirm no more than 10 orders are displayed.

---

## Usability Principles

The first desktop release should favor:

- obvious next actions;
- constrained valid inputs;
- readable plan output;
- visible canonical identity;
- consistent clearing of stale state;
- predictable deterministic results;
- minimal configuration.

It should avoid:

- hidden state;
- ambiguous empty areas;
- unbounded output;
- modal-dialog-heavy workflows;
- backend terminology without explanation;
- premature visual complexity.

---

## Success Criteria

The workflow design is successful if a user unfamiliar with canonical SIDs can select a valid target, generate a plan, understand the required construction sequence and costs, recover from errors, and change targets without stale or contradictory information remaining on screen.
