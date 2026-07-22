# BE-016 Architectural Impact Summary

BE-016 adds a projection boundary above BE-015 without changing planner-domain
contracts.

The planner remains responsible for dependency union, scheduling, completion,
and provenance. The Query Layer combines those canonical facts with existing
localization and canonical building definitions to publish stable immutable
explanation models.

Presenters can consume these contracts without importing planner graphs,
objective-planning algorithms, localization storage, parsers, or repository
paths.

No presentation behavior, objective-selection UI, persistence, comparison,
multi-town planning, optimization, or workspace lifecycle behavior is changed.
