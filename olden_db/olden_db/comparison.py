from __future__ import annotations

from dataclasses import dataclass

from .models import BuildingKey, ResourceCost
from .planner import BuildPlan


@dataclass(frozen=True, slots=True)
class PlanComparison:
    """Immutable right-minus-left comparison of two completed build plans.

    Positive deltas mean the right plan has more actions, finishes later, or
    costs more. Added buildings occur only in the right plan; removed buildings
    occur only in the left plan.
    """

    left_plan: BuildPlan
    right_plan: BuildPlan
    action_delta: int
    completion_date_delta: int
    resource_delta: ResourceCost
    added_buildings: tuple[BuildingKey, ...]
    removed_buildings: tuple[BuildingKey, ...]
    identical: bool


def compare_build_plans(left: BuildPlan, right: BuildPlan) -> PlanComparison:
    """Compare two completed plans without performing planning or I/O.

    Every delta follows ``right - left`` semantics. Construction differences
    compare unique ``BuildingKey`` membership from plan steps and are returned
    in canonical ``BuildingKey`` order.
    """
    if not isinstance(left, BuildPlan):
        raise TypeError("left must be a BuildPlan")
    if not isinstance(right, BuildPlan):
        raise TypeError("right must be a BuildPlan")

    left_buildings = _unique_action_buildings(left, side="left")
    right_buildings = _unique_action_buildings(right, side="right")

    return PlanComparison(
        left_plan=left,
        right_plan=right,
        action_delta=right.build_actions - left.build_actions,
        completion_date_delta=(
            right.completion_date.day_index - left.completion_date.day_index
        ),
        resource_delta=right.total_cost - left.total_cost,
        added_buildings=tuple(sorted(right_buildings - left_buildings)),
        removed_buildings=tuple(sorted(left_buildings - right_buildings)),
        identical=left == right,
    )


def _unique_action_buildings(
    plan: BuildPlan,
    *,
    side: str,
) -> frozenset[BuildingKey]:
    buildings = tuple(step.building for step in plan.steps)
    unique = frozenset(buildings)
    if len(buildings) != len(unique):
        raise ValueError(
            f"{side} plan contains duplicate construction action identities"
        )
    return unique
