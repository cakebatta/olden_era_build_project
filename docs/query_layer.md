# Query Layer Design Specification

## Purpose

The Query Layer is the stable public interface to the backend. It
answers planning questions by coordinating existing backend components
while hiding implementation details.

## Architecture

``` text
Game Assets
    ↓
Parsers
    ↓
Database
    ↓
Planner
    ↓
Query Layer
    ├── CLI
    ├── Desktop UI
    └── Future Integrations
```

## Responsibilities

The Query Layer may: - Accept user-oriented requests. - Coordinate
planner, graph, localization, and database modules. - Return
deterministic domain objects. - Validate inputs.

The Query Layer must not: - Parse game assets. - Implement planning
algorithms. - Contain presentation logic. - Duplicate backend business
logic.

## Initial Query Set

1.  Retrieve building information by SID.
2.  Retrieve building prerequisites.
3.  Generate a deterministic build plan.
4.  Compute cumulative resource costs.
5.  Enumerate legal build orders.

## Design Principles

-   SIDs are canonical.
-   Localization is presentation only.
-   Results are deterministic.
-   Public APIs should remain stable.

## Non-Goals

The Query Layer does not model AI, combat, random economy, or map
generation.

## Sprint 2 Acceptance Criteria

-   Dedicated query module exists.
-   Initial query set implemented.
-   Existing backend APIs unchanged.
-   Deterministic validation passes.
-   External clients interact only through the Query Layer.
