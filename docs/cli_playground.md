# Query Layer CLI Playground

## Purpose

The CLI playground is a lightweight engineering validation client for the
`PlanningQueryService`. It is not a production command-line interface and is
not intended to replace the planned desktop application.

The tool exists to verify that realistic presentation-layer workflows can be
completed through the Query Layer without reaching into parser, graph,
planner, database, or path-resolution internals.

## Run

From the outer `olden_db/` directory:

```bash
python -m scripts.query_playground
```

The playground prompts for a canonical faction, building SID, and level. Its
menu can then display:

1. building information;
2. direct prerequisites;
3. one deterministic build plan;
4. cumulative resource cost;
5. a bounded number of legal build orders.

Canonical faction, SID, and level are always retained in output. Localization
keys may be shown as supplementary presentation data, but localized text is
not used as identity.

## Build-order safety

Legal build-order output defaults to 10 orders and requires a finite limit.
The playground passes that limit to
`PlanningQueryService.enumerate_build_orders(max_orders=...)` rather than
requesting every order and truncating afterward. The interactive maximum is
100 orders.

## Error handling

Invalid factions, building SIDs, and levels are reported as readable request
errors without exposing tracebacks. Backend exceptions are not silently
ignored.

## Architectural boundary

The playground obtains planning results exclusively through
`PlanningQueryService`. It imports structured domain objects only for display
formatting and does not reproduce backend planning logic.
