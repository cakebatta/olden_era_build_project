# Heroes of Might & Magic: Olden Era Build Planner

A deterministic planning and analysis application for Heroes of Might & Magic: Olden Era.

## Current capabilities

The project includes canonical data parsing, dependency and planning engines, the public Query Layer, responsive desktop planning/comparison/economy workspaces, deterministic town income, recruitment/resource-ledger analysis, certified scenario persistence, and a persistent desktop scenario manager.

Desktop users can maintain a local scenario library with New, Open, Save, Save As, Rename, Duplicate, Delete, Import, and Export workflows. Scenario documents are stored under the operating system's per-user application-data location rather than in the source repository.

The current product direction is an interactive Planning Workspace that automatically replans from semantic player selections while preserving deterministic backend behavior.

## Repository structure

```text
docs/          Project documentation
olden_db/      Python application
```

## Documentation

Recommended reading:

1. `docs/architecture.md`
2. `docs/project_management_principles.md`
3. `docs/planning_workspace_architecture.md`
4. `docs/desktop_application_architecture.md`
5. `docs/query_layer.md`
6. `docs/scenario_planning_architecture.md`
7. `docs/scenario_persistence_architecture.md`
8. `docs/desktop_scenario_manager.md`
9. `docs/roadmap.md`

The project emphasizes deterministic behavior, explicit immutable contracts, strict ownership boundaries, interaction-independent planning semantics, and comprehensive validation.

GitHub `main` is the canonical source of truth for code and documentation.
