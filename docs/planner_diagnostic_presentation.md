# Planner Diagnostic Inspector Presentation

UI-018 refines the desktop Planner Diagnostic Inspector without changing planner,
Query Layer, presenter, or adapter behavior.

The inspector remains read-only and preserves adapter-provided ordering and
severity. Presentation improvements include responsive explanation wrapping,
overflow-aware scrollbar visibility, clearer title and severity hierarchy,
a guided empty state, Page Up/Page Down support, visible focus treatment, and
keyboard usage guidance.

Severity styling uses only `DiagnosticSeverity` values supplied by the desktop
adapter. The view does not inspect or reinterpret diagnostic explanation text.
