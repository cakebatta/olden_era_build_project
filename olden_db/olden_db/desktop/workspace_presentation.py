from __future__ import annotations

from dataclasses import dataclass

from olden_db.planning_workspace import PlanningExecutionStatus

from .planner_diagnostics import PlannerDiagnosticPresentation
from .planning_summary import PlanningSummaryPresentation


@dataclass(frozen=True, slots=True)
class PlanningWorkspacePresentation:
    """Immutable presentation projection for the single active workspace entry."""

    execution_status: PlanningExecutionStatus
    status_heading: str
    status_detail: str
    selection_summary: str
    summary: PlanningSummaryPresentation
    failure_message: str | None
    diagnostics: tuple[PlannerDiagnosticPresentation, ...]
    selection_revision: int
    result_revision: int | None

    @property
    def is_pending(self) -> bool:
        return self.execution_status is PlanningExecutionStatus.PENDING
