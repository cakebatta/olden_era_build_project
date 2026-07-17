# Heroes of Might & Magic: Olden Era Build Planner

A deterministic planning and analysis application for Heroes of Might & Magic: Olden Era.

## Current capabilities

The project includes canonical data parsing, dependency and planning engines, the public
Query Layer, responsive desktop planning/comparison/economy workspaces, deterministic
town income, recruitment/resource-ledger analysis, certified scenario persistence, and a
persistent desktop scenario manager.

Desktop users can maintain a local scenario library with New, Open, Save, Save As,
Rename, Duplicate, Delete, Import, and Export workflows. Scenario documents are stored
under the operating system's per-user application-data location rather than in the source
repository.

## Repository structure

```text
docs/          Project documentation
olden_db/      Python application
```

## Documentation

Recommended reading:

1. `docs/architecture.md`
2. `docs/roadmap.md`
3. `docs/query_layer.md`
4. `docs/scenario_persistence_architecture.md`
5. `docs/desktop_scenario_manager.md`

The project emphasizes deterministic behavior, explicit immutable contracts, strict
ownership boundaries, and comprehensive validation. GitHub is the canonical source of
truth for code and documentation.
