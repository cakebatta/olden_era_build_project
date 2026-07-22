ARCH-022 — Revised Multi-Objective Planning Architecture

Extract this ZIP directly into the repository root.

Included complete files:

docs/multi_objective_planning_architecture.md
docs/architecture.md
docs/query_layer.md

The revision explicitly addresses PM review:

1. Objective is a closed typed union, not BuildingKey.
2. Scenario/Town/ObjectiveSet/Planner ownership is explicit.
3. TownPlanningRequest owns TownState and ObjectiveSet.
4. Provenance is bidirectional, including build-step required_by objectives.
5. Query Layer additions are additive; existing APIs remain compatible.
6. Typed request failures and typed infeasibility outcomes are required.

docs/roadmap.md was reviewed and remains consistent, so it is not replaced.

No patch file is included.
No production code is included.

Suggested commit:

docs: refine multi-objective planning architecture
