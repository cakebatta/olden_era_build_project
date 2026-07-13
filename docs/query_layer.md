# Query Layer Design Specification

## Purpose

The Query Layer is the stable public interface to the backend. It answers
planning questions by coordinating existing backend components while hiding
implementation details.

## Architecture

```text
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

The Query Layer may coordinate existing database, graph, planner, and
localization modules, validate requests, and return deterministic domain
objects. It must not parse assets, duplicate algorithms, or contain
presentation logic.

## Initialization

Clients using the canonical repository game data should initialize through the
Query Layer:

```python
from olden_db.query import PlanningQueryService

queries = PlanningQueryService.from_default_game_data()
```

This encapsulates connected database initialization, so clients do not need to
import `olden_db.database`.

Explicit construction remains available for tests and callers that already
hold a `LoadedGameData` instance:

```python
queries = PlanningQueryService(loaded_data)
```

Repository path resolution remains owned by the existing database and paths
modules. Query methods themselves contain no repository-layout logic.

## Initial Public Interface

Building identity is explicit: `faction`, canonical `sid`, and `level`.

- `get_building(...) -> BuildingLevel`
- `get_prerequisites(...) -> tuple[BuildingLevel, ...]`
- `generate_build_plan(...) -> BuildPlan`
- `get_cumulative_cost(...) -> ResourceCost`
- `enumerate_build_orders(...) -> tuple[tuple[BuildingKey, ...], ...]`

The plan uses the first order yielded by the existing deterministic graph API.
Prerequisites are direct prerequisites sorted by SID and level. Formatting and
localization remain responsibilities of future clients.

Invalid requests raise `QueryError` subclasses:
`UnknownFactionError` and `UnknownBuildingError`.

## Design Principles

- SIDs are canonical.
- Localization is presentation only.
- Results are deterministic.
- Existing graph and planner algorithms remain authoritative.
- Public APIs should remain stable.
- Structured domain objects are returned without client formatting.

## Validation

From the outer `olden_db/` directory:

```bash
python -m scripts.test_query
python -m scripts.test_query_initialization
```

## Sprint 2 Acceptance Criteria

- Dedicated query module exists.
- Initial query set implemented.
- Canonical initialization is available through the Query Layer.
- Existing explicit construction remains supported.
- Existing backend APIs unchanged.
- Deterministic validation passes.
- External clients can obtain initial planning information through the Query Layer.
