# Roadmap

## Project direction

The Heroes of Might & Magic: Olden Era Build Planner is a deterministic town-planning and analysis application.

Its primary goal is to become the best possible tool for planning town development, resource use, recruitment, and related deterministic decisions. The project is not intended to become a complete Heroes companion application or a full simulation of every gameplay system.

Development proceeds in stable architectural layers. Each sprint should build on established contracts rather than replace them without compelling architectural justification.

GitHub is the canonical source of truth for project scope, architecture, implementation status, and future planning.

## Completed

- Project structure and canonical data models
- Building and unit parsers
- Dependency graph and deterministic planner
- Localization and database integration
- Public Query Layer
- Responsive desktop planning, comparison, and economy workspaces
- Recruitment, town-income, and ResourceLedger integration
- Scenario persistence product specification and certified implementation
- Persistent desktop scenario manager
- Invalid-edit protection, deferred validation, and unsaved-work safeguards
- Scenario lifecycle support for New, Open, Save, Save As, Rename, Duplicate, Delete, Import, and Export

## Current milestone

Sprint 11 — Scenario Management is complete.

The current application baseline includes certified persistence, a persistent scenario library, protected dirty-state handling, immutable scenario documents, conflict-safe repository operations, and regeneration through the public Query Layer.

These contracts are considered stable foundations for future work.

## Planned roadmap

| Sprint | Theme | Status |
|---|---|---|
| 12 | User Workflow and Planner Experience | Planned |
| 13 | Scenario Comparison Engine | Planned |
| 15 | Optimization Engine | Planned |
| 16 | Combat Analysis Tools | Planned optional module |

Sprint 14 and the former open-ended Sprint 17+ expansion category have been removed from the roadmap because they fall outside the intended scope of the project.

## Sprint 12 — User Workflow and Planner Experience

### Goal

Improve the usability, clarity, and presentation of the existing planner without redesigning its underlying planning architecture.

This sprint should make the application feel like a polished desktop product while preserving the existing Query Layer, persistence, parser, planner, and ownership boundaries.

### Candidate work

- Improve the Scenario Library
- Add scenario search, filtering, and sorting
- Support recent scenarios
- Support favorite or pinned scenarios
- Improve Build Plan presentation
- Improve Resource Ledger presentation
- Improve Income Timeline presentation
- Improve navigation between planner workspaces
- Refine desktop workflows and general usability
- Improve empty, loading, validation, and error states where needed

### Constraints

- Avoid unnecessary backend redesign.
- Do not duplicate Query Layer responsibilities in the UI.
- Preserve immutable scenario and persistence contracts.
- Keep deterministic behavior and test coverage.

## Sprint 13 — Scenario Comparison Engine

### Goal

Allow users to compare two persisted or active scenarios directly.

The comparison feature should make meaningful planning differences visible without requiring users to inspect two scenarios manually.

### Candidate comparisons

- Completion dates
- Build-order differences
- Resource expenditures
- Resource income
- Resource surpluses and deficits
- Recruitment differences
- Economic differences
- Milestone timing
- Other deterministic outputs already owned by the Query Layer

### Constraints

- Build on Scenario Management and persistence rather than introducing a parallel scenario model.
- Derive comparison results from public application services.
- Keep presentation separate from comparison logic.
- Do not persist derived comparison results unless a later specification explicitly requires it.

## Sprint 15 — Optimization Engine

### Goal

Extend the planner from answering:

> Can this plan be completed?

toward answering:

> What is the best valid plan under the selected objective and constraints?

### Candidate optimization goals

- Fastest completion
- Minimum gold expenditure
- Minimum rare-resource expenditure
- Maximum economic growth
- Maximum army growth
- User-defined deterministic constraints

### Constraints

- Optimization must build on the existing parser, graph, planner, and Query Layer.
- It must not replace the deterministic planning engine with a separate competing architecture.
- Optimization objectives and constraints must be explicit and testable.
- Stochastic map income and other random external inputs remain outside scope.

## Sprint 16 — Combat Analysis Tools

### Position in the product

Sprint 16 is an optional module separate from the core town-planning workflow.

It may share canonical game data, common UI infrastructure, and established application conventions, but it must remain logically independent from the planning engine. Combat-analysis code should not create new responsibilities for scenario persistence or town-planning services.

The module is intentionally narrow and contains three planned tools.

### CA-001 — Attack and Defense Scaling Explorer

Provide an interactive view of the game's raw attack-versus-defense scaling.

#### Inputs

- Attacker Attack
- Defender Defense
- Optional positive or negative stat adjustments

#### Outputs

- Effective Attack and Defense values
- Attack/Defense difference
- Damage multiplier produced by the game's scaling rule
- Clear presentation of how additional or reduced Attack and Defense change the result

Optional graphing may be added when it materially improves understanding.

### CA-002 — Effective Hit Point Calculator

Calculate the effective durability of a unit after combining unit statistics, hero statistics, and temporary positive or negative modifiers.

#### Inputs

- Unit base Attack
- Unit base Defense
- Hero Attack
- Hero Defense
- Added Attack or Defense
- Subtracted Attack or Defense
- Unit hit points or stack hit points, as required by the final specification

Negative adjustments are required because some spells and effects reduce Attack or Defense.

#### Outputs

- Final Attack
- Final Defense
- Effective hit points
- Relative durability compared with the unmodified unit
- Percentage increase or decrease in durability
- The effect of adding or subtracting Attack and Defense

The exact EHP baseline and formula must be defined explicitly before implementation and covered by tests.

### CA-003 — Unit Comparator

Compare two units directly in both attack directions.

#### Inputs for each unit

- Base Attack
- Base Defense
- Hero Attack
- Hero Defense
- Added or subtracted Attack
- Added or subtracted Defense
- Base damage or damage range
- Any other deterministic input required by the game's confirmed damage formula

#### Outputs

For Unit A attacking Unit B:

- Effective Attack/Defense difference
- Damage multiplier
- Resulting damage or damage range

For Unit B attacking Unit A:

- Effective Attack/Defense difference
- Damage multiplier
- Resulting damage or damage range

The comparison should clearly show how much damage each unit deals to and takes from the other based on their final Attack, Defense, and base damage values.

### Combat-module constraints

- Use confirmed game formulas only.
- Keep raw formula logic separate from presentation.
- Reuse canonical unit data where appropriate.
- Do not turn the module into a complete battle simulator.
- Do not add movement, initiative, morale, luck, battlefield positioning, spell simulation, AI, or stochastic combat systems unless separately approved in a future roadmap revision.

## Version 1 scope

Version 1 centers on deterministic town planning and closely related analysis.

Core scope includes:

- Town building prerequisites
- Legal build orders
- Construction timing
- Resource costs and income
- Recruitment costs and timing
- Build plans
- Resource ledgers
- Income timelines
- Scenario persistence and management
- Scenario comparison
- Deterministic optimization
- The optional, narrowly scoped Combat Analysis Tools module

## Out of scope

The following categories are intentionally excluded from the current roadmap:

- What-if analysis as a separate sprint category
- Hero movement simulation
- Multiple-town planning
- Map exploration
- Random map income
- Mines and external map-object simulation
- Artifact management
- Campaign systems
- Multiplayer planning
- Save-game import
- AI gameplay
- Full combat simulation
- General-purpose Heroes companion functionality
- Open-ended advanced gameplay expansion

These are product boundaries, not missing requirements.

## Engineering principles

Future work must preserve:

- deterministic behavior
- canonical SIDs
- localization as presentation
- reusable, path-agnostic parsers
- repository-layout ownership in `paths.py`
- immutable public contracts where established
- Query Layer ownership of application analysis
- persistence ownership boundaries
- conflict-safe scenario operations
- explicit validation
- comprehensive automated tests
- repository-first documentation

Every sprint should leave the project more stable, more maintainable, better documented, and less dependent on conversation history.
