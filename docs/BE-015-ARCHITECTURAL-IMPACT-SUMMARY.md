# BE-015 Architectural Impact Summary

The canonical planning input becomes `TownPlanningRequest`, owning one
`TownState` and one immutable `ObjectiveSet`.

The Query Layer remains the public validation and invocation boundary. Existing
single-target methods remain public and internally adapt to one objective.

Canonical identity, localization ownership, persistence, comparison, workspace
lifecycle, and presentation remain unchanged. Multi-town planning, optimization,
UI exposure, and persistence migration remain out of scope.
