# Query Layer Design Specification

## Purpose

The Query Layer is the stable public interface to the backend. It answers
planning questions by coordinating existing backend components while hiding
implementation details.

## Responsibilities

The Query Layer may coordinate existing database, graph, planner, and
localization modules, validate requests, return deterministic domain objects,
and expose canonical discovery information. It must not parse assets, duplicate
algorithms, expose connected backend state, or contain presentation logic.

## Initialization

```python
from olden_db.query import PlanningQueryService

queries = PlanningQueryService.from_default_game_data()
```

Explicit construction remains available for tests and callers that already
hold a `LoadedGameData` instance:

```python
queries = PlanningQueryService(loaded_data)
```

The supplied backend data is private service state. Application clients must
use only the documented Query Layer operations.

## Discovery Interface

Discovery methods return immutable tuples of canonical identifiers. They do not
return localized text or expose backend collections.

- `list_factions() -> tuple[str, ...]`
- `list_buildings(faction) -> tuple[str, ...]`
- `list_building_levels(faction, sid) -> tuple[int, ...]`

Factions and building SIDs are returned in lexical order. Building levels are
returned in ascending numeric order. Unknown factions raise
`UnknownFactionError`; unknown SIDs raise `UnknownBuildingError`.

## Planning Interface

- `get_building(...) -> BuildingLevel`
- `get_prerequisites(...) -> tuple[BuildingLevel, ...]`
- `generate_build_plan(...) -> BuildPlan`
- `get_cumulative_cost(...) -> ResourceCost`
- `enumerate_build_orders(...) -> tuple[tuple[BuildingKey, ...], ...]`

## Validation

From the outer `olden_db/` directory:

```bash
python -m scripts.test_query
python -m scripts.test_query_initialization
python -m scripts.test_query_discovery
```
