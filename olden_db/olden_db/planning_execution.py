from __future__ import annotations

from dataclasses import dataclass

from .planner import PlannerError
from .query import PlanningQueryService, QueryError
from .scenario import ScenarioError
from .planning_workspace import (
    BasePlanId,
    DEFAULT_BASE_PLAN_ID,
    PlanningExecutionRequest,
    PlanningFailureState,
    PlanningWorkspace,
    PlanningWorkspaceSnapshot,
)


@dataclass(frozen=True, slots=True)
class PlanningExecutionOutcome:
    """Result of one synchronous application-level execution attempt."""

    request: PlanningExecutionRequest
    accepted: bool
    snapshot: PlanningWorkspaceSnapshot


class PlanningExecutionCoordinator:
    """
    Synchronous Query Layer coordinator with revision-based stale rejection.

    The coordinator owns invocation timing only. It does not implement planner,
    graph, diagnostic, scheduling, debounce, or UI behavior.
    """

    __slots__ = ("_service",)

    def __init__(self, service: PlanningQueryService) -> None:
        required = ("generate_planner_result",)
        if any(not callable(getattr(service, name, None)) for name in required):
            raise TypeError(
                "service must provide PlanningQueryService.generate_planner_result"
            )
        self._service = service

    def execute(
        self,
        workspace: PlanningWorkspace,
        base_id: BasePlanId = DEFAULT_BASE_PLAN_ID,
    ) -> PlanningExecutionOutcome:
        if not isinstance(workspace, PlanningWorkspace):
            raise TypeError("workspace must be a PlanningWorkspace")

        request = workspace.capture_execution(base_id)
        selection = request.selection

        try:
            result = self._service.generate_planner_result(
                selection.faction,
                selection.target.sid,
                selection.target.level,
                starting_date=selection.starting_date,
                scenario=selection.scenario,
            )
        except (QueryError, PlannerError, ScenarioError) as exc:
            accepted = workspace.accept_failure(
                request,
                PlanningFailureState.from_exception(exc),
            )
        else:
            accepted = workspace.accept_result(request, result)

        return PlanningExecutionOutcome(
            request=request,
            accepted=accepted,
            snapshot=workspace.snapshot(),
        )
