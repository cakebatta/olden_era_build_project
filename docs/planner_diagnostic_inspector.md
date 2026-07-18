# Planner Diagnostic Inspector

The desktop Build Planner includes a read-only Diagnostic Inspector beneath Planning Results. It displays every canonical planner diagnostic returned for successful and failed planning attempts, preserves backend ordering, and replaces stale diagnostics after each attempt.

The Query Layer exposes the additive `PlanningQueryService.generate_planner_result(...)` orchestration method. Existing `generate_build_plan(...)` callers remain compatible. The desktop presenter adapts canonical diagnostics into immutable presentation models; the view only renders those models.

The inspector displays title, canonical explanation, and visual severity. Explanations are not rewritten. The panel supports vertical scrolling and keyboard navigation with Up, Down, Home, and End. Focused diagnostic entries have a visible focus indicator. When no diagnostics are present, the inspector displays `No diagnostics.`
