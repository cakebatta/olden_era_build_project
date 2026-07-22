# BE-016 Query Layer API Summary

## Operation

```python
generate_objective_plan_view(
    request: TownPlanningRequest
) -> MultiObjectivePlanningResultView | ObjectivePlanningFailure
```

Invalid requests continue to raise the BE-015 typed request exceptions.
Structurally valid infeasibility continues to return the BE-015 typed failure.

`MultiObjectivePlanningResultView` exposes:

- a top-level objective-planning summary;
- one completion view per explicit objective;
- objective-facing prerequisite provenance;
- one explanation per integrated build action;
- immutable planner diagnostics.

Localized strings are resolved exclusively through existing
`PlanningQueryService` localization operations. Canonical identity remains
present beside display text.

No planner graph, localization catalog, parser state, repository path, presenter
state, or workspace lifecycle data is exposed.
