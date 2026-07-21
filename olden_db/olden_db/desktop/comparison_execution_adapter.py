from __future__ import annotations

from dataclasses import dataclass

from olden_db.planning_workspace import (
    DEFAULT_BASE_PLAN_ID,
    BasePlanId,
    PlanningWorkspace,
    PlanningWorkspaceSnapshot,
)
from olden_db.scenario_comparison import (
    ScenarioComparisonCollection,
    ScenarioComparisonExecutionCoordinator,
    WorkspaceId,
)


@dataclass(frozen=True, slots=True)
class WorkspaceExecutionOutcome:
    snapshot: PlanningWorkspaceSnapshot


class CollectionWorkspaceExecutionAdapter:
    """Adapt one collection member to the existing PlannerPresenter contract."""

    def __init__(
        self,
        collection: ScenarioComparisonCollection,
        coordinator: ScenarioComparisonExecutionCoordinator,
        workspace_id: WorkspaceId,
    ) -> None:
        self._collection = collection
        self._coordinator = coordinator
        self._workspace_id = workspace_id

    def execute(
        self,
        workspace: PlanningWorkspace,
        base_id: BasePlanId = DEFAULT_BASE_PLAN_ID,
    ) -> WorkspaceExecutionOutcome:
        if workspace is not self._collection.workspace(self._workspace_id):
            raise ValueError("execution adapter received the wrong PlanningWorkspace")
        outcome = self._coordinator.execute(
            self._collection,
            self._workspace_id,
            base_id,
        )
        return WorkspaceExecutionOutcome(
            snapshot=outcome.collection_snapshot.member(
                self._workspace_id
            ).workspace
        )
