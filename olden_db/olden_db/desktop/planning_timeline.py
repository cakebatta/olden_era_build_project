from __future__ import annotations

from dataclasses import dataclass

from .build_plan_explanation import BuildStepIdentity


@dataclass(frozen=True, slots=True)
class TimelineStepPresentation:
    identity: BuildStepIdentity
    step_number: int
    position_text: str
    building_name: str
    level_text: str
    construction_date_text: str
    individual_cost_text: str
    cumulative_cost_text: str
    completion_order_text: str


@dataclass(frozen=True, slots=True)
class BuildPlanTimelinePresentation:
    result_status: str
    empty_state_text: str | None
    steps: tuple[TimelineStepPresentation, ...]
    is_retained_previous_result: bool


EMPTY_BUILD_PLAN_TIMELINE = BuildPlanTimelinePresentation(
    result_status="No accepted plan",
    empty_state_text="Complete the planning selection to view the build timeline.",
    steps=(),
    is_retained_previous_result=False,
)
