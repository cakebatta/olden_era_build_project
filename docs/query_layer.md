# Query Layer Design Specification

## Purpose

The Query Layer is the stable public interface to the backend. It answers planning questions by coordinating existing backend components while hiding implementation details.

## Responsibilities

The Query Layer may coordinate existing database, graph, planner, and localization modules, validate requests, and return deterministic domain objects. It must not parse assets, duplicate algorithms, expose connected backend state, or contain presentation logic.

## Initialization

```python
from olden_db.query import PlanningQueryService

queries = PlanningQueryService.from_default_game_data()
```

Explicit construction remains available for tests and callers that already hold a `LoadedGameData` instance:

```python
queries = PlanningQueryService(loaded_data)
```

The supplied backend data is retained as private service state. Application clients must not traverse it directly and should use only the documented Query Layer operations.

## Initial Public Interface

Building identity is explicit: `faction`, canonical `sid`, and `level`.

- `get_building(...) -> BuildingLevel`
- `get_prerequisites(...) -> tuple[BuildingLevel, ...]`
- `generate_build_plan(...) -> BuildPlan`
- `get_cumulative_cost(...) -> ResourceCost`
- `enumerate_build_orders(...) -> tuple[tuple[BuildingKey, ...], ...]`

## Design Principles

- SIDs are canonical.
- Localization is presentation only.
- Results are deterministic.
- Existing graph and planner algorithms remain authoritative.
- Connected backend state is private to the Query Layer.
- Structured domain objects are returned without client formatting.

## Validation

```bash
python -m scripts.test_query
python -m scripts.test_query_initialization
```
