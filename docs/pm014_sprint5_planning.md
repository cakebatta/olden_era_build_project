# PM-014 — Sprint 5 Planning & Roadmap Refresh

## Purpose
Close Sprint 4, synchronize project documentation, and prepare the repository for Sprint 5.

## Update docs/roadmap.md
- Mark Version 0.1.0 (Deterministic Planner Foundation) complete.
- Mark Version 0.2.0 (Scenario Planning) complete.
- Set Sprint 5 as active.
- Prioritize:
  1. Plan Comparison
  2. Alternative Legal Build Orders
  3. Optimization Tools

## Update docs/project_history.md
Record Version 0.2.0:
- Immutable scenario contracts
- Scenario-aware Query Layer
- Desktop scenario controls
- End-to-end QA certification

## Update docs/architecture.md
Add:
> Canonical planning is the reference model.
> Scenario planning is an explicit transformation of that model.

Also document:
- Scenario semantics end at the Query Layer.
- The graph receives only effective starting buildings.
- The planner remains scenario-independent.

## Technical Debt
- TD-001: Strengthen scenario regression assertions.
- TD-002: Expand immutability verification.
- TD-003: Clarify scenario exception documentation.

## Sprint 5 Theme
Comparative Planning

Goals:
- Compare canonical vs. scenario plans.
- Resource deltas.
- Completion-date comparison.
- Action-count comparison.
- Highlight added/removed construction.

Comparison must consume immutable Query Layer results and never duplicate planner logic.

## Exit Criteria
Documentation updated and roadmap reflects Sprint 5 priorities.
