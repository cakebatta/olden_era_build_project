from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from olden_db.planner_diagnostics import (
    PlannerDiagnostic,
    PlannerDiagnosticCategory,
)


class DiagnosticSeverity(str, Enum):
    """Desktop-only visual severity for the diagnostic inspector."""

    ERROR = "Error"
    WARNING = "Warning"
    INFORMATION = "Information"


@dataclass(frozen=True, slots=True)
class PlannerDiagnosticPresentation:
    """Immutable desktop adapter value prepared for rendering."""

    title: str
    explanation: str
    severity: DiagnosticSeverity

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("diagnostic title cannot be blank")
        if not self.explanation.strip():
            raise ValueError("diagnostic explanation cannot be blank")
        if not isinstance(self.severity, DiagnosticSeverity):
            raise TypeError("severity must be a DiagnosticSeverity")


_TITLES = {
    "PLANNER_FACTION_MISMATCH": "Faction mismatch",
    "PLANNER_INVALID_BUILD_ORDER": "Invalid build order",
    "PLANNER_GRAPH_NODE_MISSING_FROM_CITY": "Planner data is inconsistent",
    "PLANNER_EMPTY_PLAN_SET": "No plans were produced",
    "PLANNER_PLAN_SET_MULTIPLE_FACTIONS": "Plan set contains multiple factions",
    "PLANNER_PLAN_SET_MULTIPLE_TARGETS": "Plan set contains multiple targets",
    "PLANNER_PLAN_SET_MULTIPLE_STARTING_DATES": "Plan set contains multiple starting dates",
    "PLANNER_PLAN_SET_INCONSISTENT_ACTION_COUNTS": "Plan action counts differ",
    "PLANNER_PLAN_SET_INCONSISTENT_TOTAL_COSTS": "Plan costs differ",
    "PLANNER_PLAN_SET_INCONSISTENT_COMPLETION_DATES": "Plan completion dates differ",
    "PLANNER_PLAN_SET_DUPLICATE_ORDER": "Duplicate build order",
}

_SEVERITIES = {
    PlannerDiagnosticCategory.INVALID_REQUEST: DiagnosticSeverity.ERROR,
    PlannerDiagnosticCategory.INVALID_BUILD_ORDER: DiagnosticSeverity.ERROR,
    PlannerDiagnosticCategory.DATA_INTEGRITY: DiagnosticSeverity.ERROR,
    PlannerDiagnosticCategory.CONSISTENCY: DiagnosticSeverity.ERROR,
}


def adapt_planner_diagnostic(
    diagnostic: PlannerDiagnostic,
) -> PlannerDiagnosticPresentation:
    """Translate one canonical planner fact into desktop presentation data."""
    if not isinstance(diagnostic, PlannerDiagnostic):
        raise TypeError("diagnostic must be a PlannerDiagnostic")
    return PlannerDiagnosticPresentation(
        title=_TITLES.get(
            diagnostic.diagnostic_code,
            diagnostic.diagnostic_code.replace("_", " ").title(),
        ),
        explanation=diagnostic.canonical_explanation,
        severity=_SEVERITIES[diagnostic.category],
    )


def adapt_planner_diagnostics(
    diagnostics: tuple[PlannerDiagnostic, ...],
) -> tuple[PlannerDiagnosticPresentation, ...]:
    """Translate canonical diagnostics without adding planner behavior."""
    return tuple(adapt_planner_diagnostic(item) for item in diagnostics)
