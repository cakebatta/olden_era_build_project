from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from uuid import uuid4

from .planner import PlannerError, PlannerResult
from .planning_workspace import (
    DEFAULT_BASE_PLAN_ID,
    BasePlanId,
    PlanningExecutionRequest,
    PlanningFailureState,
    PlanningSelection,
    PlanningWorkspace,
    PlanningWorkspaceSnapshot,
)
from .query import PlanningQueryService, QueryError
from .scenario import ScenarioError


@dataclass(frozen=True, slots=True, order=True)
class WorkspaceId:
    """Stable opaque application identity for one Planning Workspace."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("workspace id must be a non-blank string")

    @classmethod
    def new(cls) -> "WorkspaceId":
        return cls(uuid4().hex)


class ComparisonRole(str, Enum):
    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True, slots=True)
class ScenarioComparisonMemberSnapshot:
    workspace_id: WorkspaceId
    order_index: int
    label: str
    comparison_role: ComparisonRole | None
    workspace: PlanningWorkspaceSnapshot

    def __post_init__(self) -> None:
        if self.order_index < 0:
            raise ValueError("order_index cannot be negative")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("workspace label must be non-blank")
        if (
            self.comparison_role is not None
            and not isinstance(self.comparison_role, ComparisonRole)
        ):
            raise TypeError("comparison_role must be ComparisonRole or None")
        if not isinstance(self.workspace, PlanningWorkspaceSnapshot):
            raise TypeError("workspace must be PlanningWorkspaceSnapshot")


@dataclass(frozen=True, slots=True)
class ScenarioComparisonCollectionSnapshot:
    collection_revision: int
    members: tuple[ScenarioComparisonMemberSnapshot, ...]

    def __post_init__(self) -> None:
        if self.collection_revision < 0:
            raise ValueError("collection_revision cannot be negative")
        normalized = tuple(self.members)
        if not normalized:
            raise ValueError("comparison collection requires at least one workspace")
        ids = tuple(member.workspace_id for member in normalized)
        if len(set(ids)) != len(ids):
            raise ValueError("workspace ids must be unique")
        if tuple(member.order_index for member in normalized) != tuple(range(len(normalized))):
            raise ValueError("order indexes must be contiguous")
        roles = tuple(
            member.comparison_role
            for member in normalized
            if member.comparison_role is not None
        )
        if len(set(roles)) != len(roles):
            raise ValueError("comparison roles must be unique")
        object.__setattr__(self, "members", normalized)

    def member(self, workspace_id: WorkspaceId) -> ScenarioComparisonMemberSnapshot:
        for member in self.members:
            if member.workspace_id == workspace_id:
                return member
        raise KeyError(f"unknown workspace id: {workspace_id.value}")


@dataclass(frozen=True, slots=True)
class CorrelatedPlanningExecutionRequest:
    workspace_id: WorkspaceId
    workspace_request: PlanningExecutionRequest

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, WorkspaceId):
            raise TypeError("workspace_id must be WorkspaceId")
        if not isinstance(self.workspace_request, PlanningExecutionRequest):
            raise TypeError("workspace_request must be PlanningExecutionRequest")

    @property
    def selection(self) -> PlanningSelection:
        return self.workspace_request.selection

    @property
    def selection_revision(self) -> int:
        return self.workspace_request.selection_revision


@dataclass(frozen=True, slots=True)
class CorrelatedPlanningExecutionOutcome:
    request: CorrelatedPlanningExecutionRequest
    accepted: bool
    collection_snapshot: ScenarioComparisonCollectionSnapshot


@dataclass(frozen=True, slots=True)
class _CollectionMember:
    workspace_id: WorkspaceId
    workspace: PlanningWorkspace
    label: str
    comparison_role: ComparisonRole | None = None


class ScenarioComparisonCollection:
    """Application-scoped owner of ordered independent Planning Workspaces."""

    __slots__ = ("_members", "_collection_revision")

    def __init__(
        self,
        members: tuple[_CollectionMember, ...] | None = None,
        *,
        collection_revision: int = 0,
    ) -> None:
        if collection_revision < 0:
            raise ValueError("collection_revision cannot be negative")
        initial = (
            (
                _CollectionMember(
                    workspace_id=WorkspaceId.new(),
                    workspace=PlanningWorkspace.create(),
                    label="Scenario 1",
                ),
            )
            if members is None
            else tuple(members)
        )
        if not initial:
            raise ValueError("comparison collection requires at least one workspace")
        self._members = initial
        self._collection_revision = collection_revision
        self.snapshot()

    @classmethod
    def create(cls) -> "ScenarioComparisonCollection":
        return cls()

    @property
    def collection_revision(self) -> int:
        return self._collection_revision

    @property
    def workspace_ids(self) -> tuple[WorkspaceId, ...]:
        return tuple(member.workspace_id for member in self._members)

    def snapshot(self) -> ScenarioComparisonCollectionSnapshot:
        return ScenarioComparisonCollectionSnapshot(
            collection_revision=self._collection_revision,
            members=tuple(
                ScenarioComparisonMemberSnapshot(
                    workspace_id=member.workspace_id,
                    order_index=index,
                    label=member.label,
                    comparison_role=member.comparison_role,
                    workspace=member.workspace.snapshot(),
                )
                for index, member in enumerate(self._members)
            ),
        )

    def workspace(self, workspace_id: WorkspaceId) -> PlanningWorkspace:
        return self._member(workspace_id).workspace

    def create_workspace(
        self,
        *,
        label: str | None = None,
        comparison_role: ComparisonRole | None = None,
    ) -> WorkspaceId:
        workspace_id = WorkspaceId.new()
        resolved_label = label or f"Scenario {len(self._members) + 1}"
        self._validate_label(resolved_label)
        self._validate_role_available(comparison_role)
        self._members = (
            *self._members,
            _CollectionMember(
                workspace_id=workspace_id,
                workspace=PlanningWorkspace.create(),
                label=resolved_label,
                comparison_role=comparison_role,
            ),
        )
        self._collection_revision += 1
        return workspace_id

    def duplicate_workspace(
        self,
        source_workspace_id: WorkspaceId,
        *,
        label: str | None = None,
        comparison_role: ComparisonRole | None = None,
        base_id: BasePlanId = DEFAULT_BASE_PLAN_ID,
    ) -> WorkspaceId:
        source_selection = self.workspace(source_workspace_id).base(base_id).selection
        duplicate_id = self.create_workspace(
            label=label,
            comparison_role=comparison_role,
        )
        if source_selection is not None:
            self.workspace(duplicate_id).replace_selection(source_selection, base_id)
        return duplicate_id

    def remove_workspace(self, workspace_id: WorkspaceId) -> None:
        if len(self._members) == 1:
            raise ValueError("cannot remove final workspace")
        before = len(self._members)
        self._members = tuple(
            member for member in self._members if member.workspace_id != workspace_id
        )
        if len(self._members) == before:
            raise KeyError(f"unknown workspace id: {workspace_id.value}")
        self._collection_revision += 1

    def reorder_workspace(self, workspace_id: WorkspaceId, new_index: int) -> None:
        if not 0 <= new_index < len(self._members):
            raise IndexError("new_index outside collection")
        current_index = next(
            (
                index
                for index, member in enumerate(self._members)
                if member.workspace_id == workspace_id
            ),
            None,
        )
        if current_index is None:
            raise KeyError(f"unknown workspace id: {workspace_id.value}")
        if current_index == new_index:
            return
        items = list(self._members)
        member = items.pop(current_index)
        items.insert(new_index, member)
        self._members = tuple(items)
        self._collection_revision += 1

    def set_label(self, workspace_id: WorkspaceId, label: str) -> None:
        self._validate_label(label)
        member = self._member(workspace_id)
        if member.label == label:
            return
        self._replace_member(replace(member, label=label))
        self._collection_revision += 1

    def set_comparison_role(
        self,
        workspace_id: WorkspaceId,
        role: ComparisonRole | None,
    ) -> None:
        member = self._member(workspace_id)
        if member.comparison_role == role:
            return
        self._validate_role_available(role, excluding=workspace_id)
        self._replace_member(replace(member, comparison_role=role))
        self._collection_revision += 1

    def capture_execution(
        self,
        workspace_id: WorkspaceId,
        base_id: BasePlanId = DEFAULT_BASE_PLAN_ID,
    ) -> CorrelatedPlanningExecutionRequest:
        return CorrelatedPlanningExecutionRequest(
            workspace_id=workspace_id,
            workspace_request=self.workspace(workspace_id).capture_execution(base_id),
        )

    def accept_result(
        self,
        request: CorrelatedPlanningExecutionRequest,
        result: PlannerResult,
    ) -> bool:
        workspace = self._workspace_for_request(request)
        return False if workspace is None else workspace.accept_result(
            request.workspace_request,
            result,
        )

    def accept_failure(
        self,
        request: CorrelatedPlanningExecutionRequest,
        failure: PlanningFailureState,
    ) -> bool:
        workspace = self._workspace_for_request(request)
        return False if workspace is None else workspace.accept_failure(
            request.workspace_request,
            failure,
        )

    def _workspace_for_request(
        self,
        request: CorrelatedPlanningExecutionRequest,
    ) -> PlanningWorkspace | None:
        if not isinstance(request, CorrelatedPlanningExecutionRequest):
            raise TypeError("request must be CorrelatedPlanningExecutionRequest")
        try:
            return self.workspace(request.workspace_id)
        except KeyError:
            return None

    def _member(self, workspace_id: WorkspaceId) -> _CollectionMember:
        if not isinstance(workspace_id, WorkspaceId):
            raise TypeError("workspace_id must be WorkspaceId")
        for member in self._members:
            if member.workspace_id == workspace_id:
                return member
        raise KeyError(f"unknown workspace id: {workspace_id.value}")

    def _replace_member(self, updated: _CollectionMember) -> None:
        self._members = tuple(
            updated if member.workspace_id == updated.workspace_id else member
            for member in self._members
        )

    def _validate_role_available(
        self,
        role: ComparisonRole | None,
        *,
        excluding: WorkspaceId | None = None,
    ) -> None:
        if role is None:
            return
        if not isinstance(role, ComparisonRole):
            raise TypeError("role must be ComparisonRole or None")
        if any(
            member.comparison_role is role and member.workspace_id != excluding
            for member in self._members
        ):
            raise ValueError(f"comparison role {role.value!r} already assigned")

    @staticmethod
    def _validate_label(label: str) -> None:
        if not isinstance(label, str) or not label.strip():
            raise ValueError("workspace label must be non-blank")


class ScenarioComparisonExecutionCoordinator:
    """Shared synchronous Query Layer coordinator for all collection members."""

    __slots__ = ("_service",)

    def __init__(self, service: PlanningQueryService) -> None:
        if not callable(getattr(service, "generate_planner_result", None)):
            raise TypeError(
                "service must provide PlanningQueryService.generate_planner_result"
            )
        self._service = service

    @property
    def service(self) -> PlanningQueryService:
        return self._service

    def execute(
        self,
        collection: ScenarioComparisonCollection,
        workspace_id: WorkspaceId,
        base_id: BasePlanId = DEFAULT_BASE_PLAN_ID,
    ) -> CorrelatedPlanningExecutionOutcome:
        if not isinstance(collection, ScenarioComparisonCollection):
            raise TypeError("collection must be ScenarioComparisonCollection")

        request = collection.capture_execution(workspace_id, base_id)
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
            accepted = collection.accept_failure(
                request,
                PlanningFailureState.from_exception(exc),
            )
        else:
            accepted = collection.accept_result(request, result)

        return CorrelatedPlanningExecutionOutcome(
            request=request,
            accepted=accepted,
            collection_snapshot=collection.snapshot(),
        )
