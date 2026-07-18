# ARCH-018 — Planner Diagnostic Ownership

Status: Accepted  
Decision source: ACR-001  
Applies to: BE-017 — Planner Diagnostic Interface

## Context

The desktop constraint inspector originally consumed
`PlannerDiagnosticPresentation`, a presentation-oriented value containing a
title, explanation, and visual severity. That type could not serve as the
canonical planner diagnostic contract because it mixed planner facts with
desktop presentation concerns.

The planner must expose structured, deterministic facts while preserving the
existing exception-based failure behavior and stable Query Layer callers.

## Decision

The planner owns an immutable `PlannerDiagnostic` model containing:

- a stable diagnostic code;
- a backend category;
- a canonical explanation;
- affected canonical entities; and
- optional immutable structured metadata.

`PlannerResult` carries a successful `BuildPlan` and a tuple of canonical
diagnostics.

Planning failures remain exception based. `PlanningFailure` carries a non-empty
tuple of canonical diagnostics. Existing `PlannerError` compatibility is
preserved, and specialized planner failures remain catchable through the
existing hierarchy.

The historical `plan_build_order` function continues to return `BuildPlan`.
The additive `plan_build_order_result` interface exposes `PlannerResult` to new
callers without breaking existing Query Layer contracts.

## Presentation ownership

`PlannerDiagnosticPresentation` remains a desktop-only adapter value.

The desktop adapter translates canonical diagnostics into presentation data,
including:

- display title;
- visual severity;
- future localization;
- future ordering or grouping; and
- display formatting.

The planner does not own colors, icons, presentation ordering, localization, or
other UI concepts.

The desktop presenter uses structured diagnostics from `PlanningFailure` when
available. It does not synthesize planner diagnostics from exception strings
when canonical diagnostics exist. Legacy non-planner exceptions continue to
use the existing fallback error presentation.

## Consequences

- Planner diagnostics are deterministic and independently testable.
- Existing Query Layer `BuildPlan` callers remain compatible.
- Failed planning behavior remains exception based.
- Desktop presentation can evolve without changing planner contracts.
- Future successful-plan warnings can be returned through `PlannerResult`
  without introducing a competing result model.
