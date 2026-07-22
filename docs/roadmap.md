# Roadmap

## Project direction

The Heroes of Might & Magic: Olden Era Build Planner is a deterministic scenario-planning and analysis application.

Its primary goal is to become the best possible tool for planning town development, resource use, recruitment, and related deterministic decisions. The project is not intended to become a complete Heroes companion application or a full simulation of every gameplay system.

The central product concept is the **Scenario Planning Workspace**. A scenario may contain one or more towns, each with its own starting state and planning objectives, while all towns may participate in one shared deterministic economy.

Development proceeds in stable architectural layers. Each sprint should build on established contracts rather than replace them without compelling architectural justification.

GitHub is the canonical source of truth for project scope, architecture, implementation status, and future planning.

## Product organization

The application organizes functionality by **module**, not by individual tool.

A top-level navigation entry represents a major product domain. Related capabilities remain grouped within that module as coordinated views of the same underlying scenario.

Current and planned module structure:

- **Scenario Planning**
  - planning objectives;
  - build plans;
  - economy;
  - timelines;
  - comparisons;
  - multi-town coordination;
  - deterministic optimization.
- **Combat Analysis**
  - optional, separately scoped deterministic analysis tools.

Features related to town building, recruitment, economy, resource use, and build-plan comparison belong inside the Scenario Planning module. Separate top-level tabs should not be created merely to expose another view of the same planning data.

## Completed

- Project structure and canonical data models
- Building and unit parsers
- Dependency graph and deterministic planner
- Existing localization parser and database integration
- Public Query Layer
- Responsive desktop planning, comparison, and economy workspaces
- Interactive Planning Workspace
- Scenario Comparison Workspace and accepted-plan comparison boundary
- Recruitment, town-income, and ResourceLedger integration
- Scenario persistence product specification and certified implementation
- Persistent desktop scenario manager
- Invalid-edit protection, deferred validation, and unsaved-work safeguards
- Scenario lifecycle support for New, Open, Save, Save As, Rename, Duplicate, Delete, Import, and Export
- ARCH-021 — Planner Localization Architecture
- BE-014 — Planner Localization Catalog
- UI-011 — Canonical Game Name Presentation

## Current milestone

Sprint 18 — Planner Experience

The current application baseline includes deterministic planning, persistent scenarios, scenario comparison, accepted-plan comparison, resource and income analysis, planner-facing localization, and game-facing faction, building, upgrade, unit, recruitment, and milestone names.

Planner-facing localization is now an established infrastructure boundary:

- canonical identities remain authoritative;
- localization is presentation;
- the immutable `PlannerLocalizationCatalog` is owned by the Query Layer;
- parser duplicate-key semantics remain unchanged;
- persisted scenarios continue to store canonical identity.

## Planned roadmap

| Sprint | Theme | Status |
|---|---|---|
| 17 | Presentation Infrastructure | Complete |
| 18 | Planner Experience and Multi-Objective Planning | Current |
| 19 | Multi-Town Shared-Economy Architecture | Planned |
| 20 | Multi-Town Shared-Economy Implementation | Planned |
| 21 | Deterministic Optimization | Planned |
| 22 | Combat Analysis Tools | Planned optional module |

Sprint numbering follows current authorized work orders. Earlier roadmap sprint labels remain historical and do not override current Project Management authorization.

## Sprint 17 — Presentation Infrastructure

### Status

Complete.

### Delivered

- ARCH-021 defined the planner localization boundary.
- BE-014 implemented the immutable `PlannerLocalizationCatalog`.
- UI-011 replaced canonical planner identifiers with game-facing display names in presentation.

### Established guarantees

- Existing duplicate-key validation remains unchanged.
- No first-file-wins or last-file-wins behavior.
- No handwritten game-name dictionaries.
- No UI-owned localization.
- No raw localization storage exposed through Query Layer APIs.
- Persisted scenarios continue to store canonical identity.
- Localization does not alter planner, persistence, or comparison output.

## Sprint 18 — Planner Experience and Multi-Objective Planning

### Goal

Evolve the planner from a single-target build-order calculator into an interactive planning workspace that can satisfy a deterministic set of objectives for one town.

### Multi-objective planning

A planning selection may contain multiple compatible objectives for the same town.

Example:

- Tier 6 dwelling, level 1;
- Treasury;
- Mage Guild, level 3.

The planner shall produce one legal build plan satisfying the complete objective set. It shall not merely calculate independent plans and concatenate them.

The plan must account for:

- the union of all prerequisite chains;
- shared prerequisites;
- mutually relevant ordering constraints;
- construction timing;
- resource availability;
- income changes caused by constructed buildings;
- total and incremental resource cost;
- objective completion timing.

### Interactive build-plan presentation

Build-plan steps should become selectable and explanatory.

A selected step may expose:

- canonical and localized building identity;
- construction day;
- cost;
- prerequisites;
- which objective or objectives require it;
- resource balance before and after construction;
- income changes;
- downstream buildings enabled by the step.

Views remain passive. Presenters obtain immutable explanation models through the Query Layer.

### Scenario workspace direction

Planning, build-plan explanation, economy, timeline, and comparison remain coordinated views inside the Scenario Planning module.

Existing separate navigation entries for scenario comparison, economy timeline, and plan comparison should be consolidated when practical so that related planning information is presented within one scenario-centered workspace.

### Expected work sequence

1. formalize multi-objective planning semantics;
2. define immutable objective-set and result contracts;
3. implement deterministic single-town multi-objective planning;
4. expose Query Layer APIs;
5. add clickable build-plan explanation models;
6. integrate the result into the Scenario Planning workspace;
7. consolidate redundant planning navigation.

## Sprint 19 — Multi-Town Shared-Economy Architecture

### Goal

Define the architecture for scenarios containing multiple towns that draw from one shared resource pool.

This is a major planning-model extension and requires architecture-first design before backend implementation.

### Scenario model

A scenario contains:

- one shared deterministic economy;
- one or more towns;
- an independent starting state for each town;
- an independent objective set for each town;
- one coordinated scenario schedule;
- one combined resource ledger.

```text
Planning Scenario
├── Shared Economy
│   ├── Initial resources
│   ├── Deterministic external income
│   └── Aggregate town income
└── Town Plans
    ├── Town A
    │   ├── Starting state
    │   └── Objective set
    ├── Town B
    │   ├── Starting state
    │   └── Objective set
    └── Town N
        ├── Starting state
        └── Objective set
```

### Required architectural decisions

The architecture must define:

- canonical town identity within a scenario;
- per-town faction and building state;
- per-town objective ownership;
- shared-resource ownership;
- per-town construction limits;
- daily scheduling across towns;
- income aggregation;
- deterministic tie-breaking;
- accepted multi-town plan contracts;
- persistence migration and compatibility;
- comparison semantics;
- Query Layer boundaries;
- typed failures and validation.

### Core invariant

Town plans cannot be solved independently and added together afterward.

All towns must be scheduled chronologically against the same authoritative resource ledger. Two town plans that are individually feasible may be jointly infeasible when they compete for the same resources.

## Sprint 20 — Multi-Town Shared-Economy Implementation

### Goal

Implement deterministic planning across multiple towns under one shared economy.

### Required capabilities

- add and remove towns from a scenario;
- assign a faction and starting state to each town;
- define unique or overlapping objective sets per town;
- calculate a coordinated legal schedule;
- calculate combined resource requirements;
- track town-specific and aggregate income;
- show which town consumes resources on each day;
- identify cross-town resource contention;
- calculate completion timing per objective, per town, and for the full scenario;
- expose a combined scenario ResourceLedger;
- persist multi-town scenarios;
- compare accepted multi-town plans.

### Expected analysis outputs

The application should answer:

- Can all town objectives be completed?
- What is the earliest legal coordinated schedule?
- What resources are required in total?
- When are specific resources exhausted or replenished?
- Which town or objective causes a delay?
- How does each town contribute to the shared economy?
- When does each objective complete?
- When does the entire scenario complete?

### Presentation direction

Multi-town planning remains inside the Scenario Planning module.

The workspace should allow the user to inspect:

- all towns together;
- one town in isolation;
- the shared economy;
- the combined timeline;
- objective completion;
- cross-town contention;
- accepted-plan comparison.

## Sprint 21 — Deterministic Optimization

### Goal

Extend the planner from answering:

> Can this objective set be completed?

toward answering:

> What is the best valid plan under the selected deterministic objective and constraints?

### Candidate objectives

- fastest full-scenario completion;
- fastest completion of a selected objective;
- minimum gold expenditure;
- minimum rare-resource expenditure;
- maximum economic growth;
- maximum army growth;
- specified resource reserves at completion;
- explicit user-defined deterministic constraints.

### Multi-town optimization

Optimization should operate over the same scenario model and may coordinate decisions across towns.

Optimization must build on the existing parser, canonical models, planner, Query Layer, persistence, localization, objective-set, and shared-economy boundaries. It must not create a separate competing planner architecture.

## Sprint 22 — Combat Analysis Tools

### Goal

Provide optional deterministic combat-analysis utilities as a separate product module.

Combat analysis may share canonical game data, Query Layer conventions, and planner localization for canonical units where appropriate. Combat algorithms remain logically independent from scenario planning.

### Candidate tools

- attack and defense scaling explorer;
- effective hit point calculator;
- unit comparator.

The module must use confirmed formulas, keep algorithms separate from presentation, and avoid becoming a complete battle simulator.

## Version 1 scope

Version 1 centers on deterministic scenario planning and closely related analysis.

Core scope includes:

- town building prerequisites;
- legal build orders;
- multi-objective town planning;
- construction timing;
- resource costs and income;
- recruitment costs and timing;
- build plans;
- interactive build-plan explanation;
- resource ledgers;
- income timelines;
- scenario persistence and management;
- scenario comparison;
- accepted-plan comparison;
- planner-facing localization;
- game-facing planner presentation;
- multi-town shared-economy planning;
- deterministic optimization;
- optional narrowly scoped Combat Analysis Tools.

## Out of scope

The following categories remain excluded unless separately authorized:

- general-purpose game localization;
- planner parsing of all interface localization resources;
- hero movement simulation;
- map exploration;
- random map income;
- automatic mine or external map-object simulation;
- artifact management;
- campaign systems;
- multiplayer planning;
- save-game import;
- AI gameplay;
- full combat simulation;
- general-purpose Heroes companion functionality;
- open-ended advanced gameplay expansion.

Deterministic external income may be entered as scenario data. Modeling map traversal, ownership changes, discovery, or random events remains outside the planner.

These are product boundaries, not missing requirements.

## Engineering principles

Future work must preserve:

- deterministic behavior;
- canonical SIDs and typed canonical identities;
- localization as presentation;
- unchanged existing localization-parser semantics;
- planner-scoped explicit localization indexing;
- reusable, path-agnostic parsers;
- repository-layout ownership in `paths.py`;
- immutable public contracts where established;
- Query Layer ownership of application analysis and display-name access;
- persistence ownership boundaries;
- conflict-safe scenario operations;
- explicit validation;
- comprehensive automated tests;
- repository-first documentation;
- architecture-first expansion of the planning model;
- scenario-centered presentation;
- module-level rather than feature-level top navigation.

Every sprint should leave the project more stable, more maintainable, better documented, and less dependent on conversation history.
