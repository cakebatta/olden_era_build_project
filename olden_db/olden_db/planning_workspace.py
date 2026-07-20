from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .models import BuildingKey
from .planner import GameDate, PlannerResult
from .planner_diagnostics import PlannerDiagnostic
from .scenario import PlanningScenario


@dataclass(frozen=True, slots=True, order=True)
class BasePlanId:
    """Stable application identity for one planning-workspace entry."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("base plan id must be a non-blank string")


DEFAULT_BASE_PLAN_ID = BasePlanId("base-1")


@dataclass(frozen=True, slots=True)
class PlanningSelection:
    """Immutable, interaction-independent player intent for one target."""

    faction: str
    target: BuildingKey
    starting_date: GameDate = GameDate(1, 1, 1)
    scenario: PlanningScenario = PlanningScenario()

    def __post_init__(self) -> None:
        if not isinstance(self.faction, str) or not self.faction.strip():
            raise ValueError("selection faction must be a non-blank string")
        if not isinstance(self.target, BuildingKey):
            raise TypeError("selection target must be a BuildingKey")
        if self.target.faction != self.faction:
            raise ValueError("selection target faction does not match selection faction")
        if not isinstance(self.starting_date, GameDate):
            raise TypeError("selection starting_date must be a GameDate")
        if not isinstance(self.scenario, PlanningScenario):
            raise TypeError("selection scenario must be a PlanningScenario")


class PlanningExecutionStatus(str, Enum):
    """Application lifecycle status for one base-planning entry."""

    EMPTY = "empty"
    INCOMPLETE = "incomplete"
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PlanningFailureState:
    """Immutable application projection of a documented planning failure."""

    error_type: str
    message: str
    diagnostics: tuple[PlannerDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        if not self.error_type.strip():
            raise ValueError("failure error_type cannot be blank")
        if not self.message.strip():
            raise ValueError("failure message cannot be blank")
        normalized = tuple(self.diagnostics)
        if any(not isinstance(item, PlannerDiagnostic) for item in normalized):
            raise TypeError("failure diagnostics must contain PlannerDiagnostic values")
        object.__setattr__(self, "diagnostics", normalized)

    @classmethod
    def from_exception(cls, exc: Exception) -> "PlanningFailureState":
        diagnostics = tuple(getattr(exc, "diagnostics", ()))
        return cls(
            error_type=type(exc).__name__,
            message=str(exc) or type(exc).__name__,
            diagnostics=diagnostics,
        )


@dataclass(frozen=True, slots=True)
class PlanningExecutionRequest:
    """Immutable selection and revision captured for one execution."""

    base_id: BasePlanId
    selection: PlanningSelection
    selection_revision: int

    def __post_init__(self) -> None:
        if self.selection_revision < 1:
            raise ValueError("execution revision must be at least 1")


@dataclass(frozen=True, slots=True)
class BasePlanningState:
    """Immutable state for one independently revisable base plan."""

    base_id: BasePlanId
    selection: PlanningSelection | None = None
    selection_revision: int = 0
    execution_status: PlanningExecutionStatus = PlanningExecutionStatus.EMPTY
    accepted_result: PlannerResult | None = None
    result_revision: int | None = None
    latest_failure: PlanningFailureState | None = None

    def __post_init__(self) -> None:
        if self.selection_revision < 0:
            raise ValueError("selection_revision cannot be negative")
        if self.result_revision is not None and self.result_revision < 1:
            raise ValueError("result_revision must be positive when present")
        if self.result_revision is not None and self.result_revision > self.selection_revision:
            raise ValueError("result_revision cannot exceed selection_revision")
        if self.selection is None and self.execution_status is not PlanningExecutionStatus.EMPTY:
            raise ValueError("an entry without a selection must be EMPTY")
        if self.selection is not None and self.execution_status is PlanningExecutionStatus.EMPTY:
            raise ValueError("an entry with a selection cannot be EMPTY")
        if self.accepted_result is None and self.result_revision is not None:
            raise ValueError("result_revision requires an accepted_result")
        if self.accepted_result is not None and self.result_revision is None:
            raise ValueError("accepted_result requires result_revision")
        if self.execution_status is PlanningExecutionStatus.READY:
            if self.accepted_result is None:
                raise ValueError("READY requires an accepted result")
            if self.result_revision != self.selection_revision:
                raise ValueError("READY result must match the current revision")
        if self.execution_status is PlanningExecutionStatus.FAILED:
            if self.latest_failure is None:
                raise ValueError("FAILED requires latest_failure")

    @property
    def result_is_current(self) -> bool:
        return (
            self.accepted_result is not None
            and self.result_revision == self.selection_revision
        )

    @property
    def retains_previous_result(self) -> bool:
        return self.accepted_result is not None and not self.result_is_current


@dataclass(frozen=True, slots=True)
class PlanningWorkspaceSnapshot:
    """Immutable snapshot supplied to application clients and presenters."""

    base_plans: tuple[BasePlanningState, ...]

    def __post_init__(self) -> None:
        normalized = tuple(self.base_plans)
        if not normalized:
            raise ValueError("a planning workspace requires at least one base entry")
        identifiers = tuple(item.base_id for item in normalized)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("workspace base ids must be unique")
        object.__setattr__(self, "base_plans", normalized)

    def base(self, base_id: BasePlanId = DEFAULT_BASE_PLAN_ID) -> BasePlanningState:
        for state in self.base_plans:
            if state.base_id == base_id:
                return state
        raise KeyError(f"unknown base plan id: {base_id.value}")


class PlanningWorkspace:
    """
    Application-scoped planning state with revision-based result acceptance.

    Sprint 13 exposes one base entry, while the internal ordered collection and
    stable BasePlanId preserve the approved N-base architecture.
    """

    __slots__ = ("_base_plans",)

    def __init__(
        self,
        base_plans: tuple[BasePlanningState, ...] | None = None,
    ) -> None:
        initial = (
            (BasePlanningState(DEFAULT_BASE_PLAN_ID),)
            if base_plans is None
            else tuple(base_plans)
        )
        snapshot = PlanningWorkspaceSnapshot(initial)
        self._base_plans = snapshot.base_plans

    @classmethod
    def create(cls) -> "PlanningWorkspace":
        return cls()

    def snapshot(self) -> PlanningWorkspaceSnapshot:
        return PlanningWorkspaceSnapshot(self._base_plans)

    def base(self, base_id: BasePlanId = DEFAULT_BASE_PLAN_ID) -> BasePlanningState:
        return self.snapshot().base(base_id)

    def replace_selection(
        self,
        selection: PlanningSelection,
        base_id: BasePlanId = DEFAULT_BASE_PLAN_ID,
    ) -> PlanningWorkspaceSnapshot:
        if not isinstance(selection, PlanningSelection):
            raise TypeError("selection must be a PlanningSelection")
        current = self.base(base_id)
        if current.selection == selection:
            return self.snapshot()
        updated = replace(
            current,
            selection=selection,
            selection_revision=current.selection_revision + 1,
            execution_status=PlanningExecutionStatus.PENDING,
            latest_failure=None,
        )
        self._replace_base(updated)
        return self.snapshot()

    def reset_selection(
        self,
        base_id: BasePlanId = DEFAULT_BASE_PLAN_ID,
    ) -> PlanningWorkspaceSnapshot:
        current = self.base(base_id)
        if current.selection is None:
            return self.snapshot()
        updated = BasePlanningState(
            base_id=current.base_id,
            selection=None,
            selection_revision=current.selection_revision + 1,
            execution_status=PlanningExecutionStatus.EMPTY,
            accepted_result=current.accepted_result,
            result_revision=current.result_revision,
        )
        self._replace_base(updated)
        return self.snapshot()

    def capture_execution(
        self,
        base_id: BasePlanId = DEFAULT_BASE_PLAN_ID,
    ) -> PlanningExecutionRequest:
        current = self.base(base_id)
        if current.selection is None:
            raise ValueError("cannot execute a workspace entry without a selection")
        if current.execution_status is not PlanningExecutionStatus.PENDING:
            updated = replace(
                current,
                execution_status=PlanningExecutionStatus.PENDING,
                latest_failure=None,
            )
            self._replace_base(updated)
            current = updated
        return PlanningExecutionRequest(
            base_id=current.base_id,
            selection=current.selection,
            selection_revision=current.selection_revision,
        )

    def accept_result(
        self,
        request: PlanningExecutionRequest,
        result: PlannerResult,
    ) -> bool:
        if not isinstance(request, PlanningExecutionRequest):
            raise TypeError("request must be a PlanningExecutionRequest")
        if not isinstance(result, PlannerResult):
            raise TypeError("result must be a PlannerResult")
        current = self.base(request.base_id)
        if request.selection_revision != current.selection_revision:
            return False
        if request.selection != current.selection:
            return False
        updated = replace(
            current,
            execution_status=PlanningExecutionStatus.READY,
            accepted_result=result,
            result_revision=request.selection_revision,
            latest_failure=None,
        )
        self._replace_base(updated)
        return True

    def accept_failure(
        self,
        request: PlanningExecutionRequest,
        failure: PlanningFailureState,
    ) -> bool:
        if not isinstance(request, PlanningExecutionRequest):
            raise TypeError("request must be a PlanningExecutionRequest")
        if not isinstance(failure, PlanningFailureState):
            raise TypeError("failure must be a PlanningFailureState")
        current = self.base(request.base_id)
        if request.selection_revision != current.selection_revision:
            return False
        if request.selection != current.selection:
            return False
        updated = replace(
            current,
            execution_status=PlanningExecutionStatus.FAILED,
            latest_failure=failure,
        )
        self._replace_base(updated)
        return True

    def _replace_base(self, updated: BasePlanningState) -> None:
        replaced = False
        items: list[BasePlanningState] = []
        for item in self._base_plans:
            if item.base_id == updated.base_id:
                items.append(updated)
                replaced = True
            else:
                items.append(item)
        if not replaced:
            raise KeyError(f"unknown base plan id: {updated.base_id.value}")
        self._base_plans = tuple(items)
