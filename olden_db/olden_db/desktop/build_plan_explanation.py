from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from olden_db.models import BuildingKey
from olden_db.planning_workspace import BasePlanId, DEFAULT_BASE_PLAN_ID


@dataclass(frozen=True, slots=True)
class BuildStepIdentity:
    base_plan_id: BasePlanId
    result_revision: int
    step_number: int
    building: BuildingKey

    def __post_init__(self) -> None:
        if self.result_revision < 1:
            raise ValueError("result_revision must be positive")
        if self.step_number < 1:
            raise ValueError("step_number must be positive")


class ExplanationPanelStatus(str, Enum):
    EMPTY = "empty"
    READY = "ready"
    RETAINED_PREVIOUS_RESULT = "retained_previous_result"


@dataclass(frozen=True, slots=True)
class ExplanationSectionPresentation:
    heading: str
    lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BuildPlanExplanationPresentation:
    base_plan_id: BasePlanId
    result_revision: int | None
    status: ExplanationPanelStatus
    selected_step: BuildStepIdentity | None
    heading: str
    sections: tuple[ExplanationSectionPresentation, ...]
    is_current_result: bool
    message: str | None = None


EMPTY_BUILD_PLAN_EXPLANATION = BuildPlanExplanationPresentation(
    base_plan_id=DEFAULT_BASE_PLAN_ID,
    result_revision=None,
    status=ExplanationPanelStatus.EMPTY,
    selected_step=None,
    heading="Build Step Explanation",
    sections=(),
    is_current_result=False,
    message="Select a construction step to review why it appears in the accepted plan.",
)
