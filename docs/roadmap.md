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

## Current milestone

Sprint 17 — Presentation Infrastructure establishes planner-facing localization
before UI-011 resumes.

The current application baseline includes deterministic planning, persistent
planning summaries, scenario comparison, canonical scenario persistence, and
Query Layer-owned building display text.

ARCH-021 defines the next presentation-infrastructure boundary:
`PlannerLocalizationCatalog`.

## Planned roadmap

| Sprint | Theme | Status |
|---|---|---|
| 17 | Presentation Infrastructure | In progress |
| 18 | Planner UX continuation | Planned |
| 19 | Deterministic optimization review | Planned |
| 20 | Combat Analysis Tools | Planned optional module |

Sprint numbering follows current authorized work orders. Earlier roadmap sprint
labels remain historical and do not override current Project Management
authorization.

## Sprint 17 — Presentation Infrastructure

### Goal

Provide one authoritative planner-facing localization source without changing
canonical identity, planner behavior, or existing localization-parser semantics.

### Authorized architecture

ARCH-021 introduces an immutable `PlannerLocalizationCatalog`.

The catalog:

- indexes only planner-visible canonical entities;
- uses explicit planner localization sources;
- avoids complete localization-directory scans;
- supplies deterministic faction, building, unit, upgrade, recruitment, and milestone display names;
- applies localized-name, canonical-display-name, then canonical-identifier fallback;
- is owned by the Query Layer;
- remains hidden from presenters and views.

### Follow-on implementation

BE-014 implements the catalog and Query Layer operations.

UI-011 resumes only after BE-014 is accepted.

### Constraints

- Existing duplicate-key validation remains unchanged.
- No first-file-wins or last-file-wins behavior.
- No handwritten game-name dictionaries.
- No UI-owned localization.
- No raw localization storage exposed through Query Layer APIs.
- Persisted scenarios continue to store canonical identity.
- Localization does not alter planner or comparison output.

## Planner UX continuation

After BE-014 acceptance, planner presentation work may:

- render faction display names;
- render building and upgrade display names;
- render unit and recruitment display names;
- render planner-visible milestone labels;
- support additional languages through catalog data and source policy;
- continue UI-011 without another localization-ownership redesign.

Presentation features must continue to use immutable models and passive views.

## Deterministic optimization direction

Future optimization may extend the planner from answering:

> Can this plan be completed?

toward answering:

> What is the best valid plan under the selected objective and constraints?

Candidate deterministic objectives include:

- fastest completion;
- minimum gold expenditure;
- minimum rare-resource expenditure;
- maximum economic growth;
- maximum army growth;
- explicit user-defined deterministic constraints.

Optimization must build on the existing parser, canonical models, planner, Query
Layer, and planner-localization presentation boundary. It must not create a
separate competing planner architecture.

## Combat Analysis Tools

Combat analysis remains an optional module separate from the core town-planning workflow.

It may share canonical game data, Query Layer conventions, and the Planner
Localization Catalog for planner-visible canonical units where appropriate.
Combat algorithms remain logically independent from planning.

Candidate tools remain:

- attack and defense scaling explorer;
- effective hit point calculator;
- unit comparator.

The module must use confirmed formulas, keep algorithms separate from
presentation, and avoid becoming a complete battle simulator.

## Version 1 scope

Version 1 centers on deterministic town planning and closely related analysis.

Core scope includes:

- town building prerequisites;
- legal build orders;
- construction timing;
- resource costs and income;
- recruitment costs and timing;
- build plans;
- resource ledgers;
- income timelines;
- scenario persistence and management;
- scenario comparison;
- planner-facing localization;
- deterministic optimization;
- optional narrowly scoped Combat Analysis Tools.

## Out of scope

The following categories remain excluded unless separately authorized:

- general-purpose game localization;
- planner parsing of all interface localization resources;
- hero movement simulation;
- map exploration;
- random map income;
- mines and external map-object simulation;
- artifact management;
- campaign systems;
- multiplayer planning;
- save-game import;
- AI gameplay;
- full combat simulation;
- general-purpose Heroes companion functionality;
- open-ended advanced gameplay expansion.

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
- repository-first documentation.

Every sprint should leave the project more stable, more maintainable, better documented, and less dependent on conversation history.
