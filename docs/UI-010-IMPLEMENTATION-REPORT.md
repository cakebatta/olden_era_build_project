# UI-010 Implementation Report

UI-010 adds a passive desktop presentation for the BE-013 accepted Build Plan Comparison Service.

The comparison presenter reads Left and Right role assignments from immutable Scenario Comparison Collection snapshots. It calls only `PlanningQueryService.compare_accepted_build_plans(...)` when both role members contain current accepted results.

All summary values, signed deltas, aligned rows, relationships, shared actions, and exclusive actions come directly from BE-013 contracts. The presenter does not align steps, compare identities, calculate resources, rank plans, recommend plans, or rerun planning.

A comparison-aware subclass wraps the existing Planning Workspace presenter only to issue lifecycle notifications whenever an immutable workspace snapshot is rendered. This allows the most recent successful comparison to remain visible during pending replanning and lets the new comparison replace it immediately after acceptance.

The view receives immutable presentation values only. It owns layout, row styling, keyboard-selectable Treeviews, scrolling, and responsive presentation.
