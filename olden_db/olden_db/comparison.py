from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import BuildingKey, ResourceCost
from .planner import BuildPlan, BuildStep, PlannerResult


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
    """Historical comparison operation retained for backward compatibility.

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


class BuildStepRelationship(str, Enum):
    """Closed relationship classification for one aligned comparison entry."""

    MATCHED = "matched"
    LEFT_ONLY = "left_only"
    RIGHT_ONLY = "right_only"
    DIFFERENT = "different"


class BuildPlanComparisonStatus(str, Enum):
    """Deterministic factual relationship between two valid accepted plans."""

    EQUIVALENT = "equivalent"
    DIFFERENT = "different"


class BuildPlanComparisonFailureCode(str, Enum):
    """Expected reasons an accepted-plan comparison is unavailable."""

    MISSING_LEFT_ACCEPTED_PLAN = "missing_left_accepted_plan"
    MISSING_RIGHT_ACCEPTED_PLAN = "missing_right_accepted_plan"
    INVALID_LEFT_PLAN_DATA = "invalid_left_plan_data"
    INVALID_RIGHT_PLAN_DATA = "invalid_right_plan_data"


@dataclass(frozen=True, slots=True)
class AcceptedBuildPlanInput:
    """Immutable accepted planner result with optional opaque correlation metadata."""

    accepted_result: PlannerResult
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.accepted_result, PlannerResult):
            raise TypeError("accepted_result must be a PlannerResult")
        if self.correlation_id is not None:
            if not isinstance(self.correlation_id, str):
                raise TypeError("correlation_id must be a string or None")
            if not self.correlation_id.strip():
                raise ValueError("correlation_id cannot be blank")


@dataclass(frozen=True, slots=True)
class BuildStepComparison:
    """One deterministic entry in the chronological alignment of two plans."""

    comparison_position: int
    left_step: BuildStep | None
    right_step: BuildStep | None
    relationship: BuildStepRelationship
    date_delta: int | None
    individual_cost_delta: ResourceCost | None
    cumulative_cost_delta: ResourceCost | None
    building_identity_matches: bool
    building_level_matches: bool

    def __post_init__(self) -> None:
        if self.comparison_position < 1:
            raise ValueError("comparison_position must be at least 1")
        if self.left_step is None and self.right_step is None:
            raise ValueError("an aligned entry requires at least one step")
        if not isinstance(self.relationship, BuildStepRelationship):
            raise TypeError("relationship must be BuildStepRelationship")

        both = self.left_step is not None and self.right_step is not None
        if both:
            if self.date_delta is None:
                raise ValueError("paired steps require a date delta")
            if self.individual_cost_delta is None:
                raise ValueError("paired steps require an individual-cost delta")
            if self.cumulative_cost_delta is None:
                raise ValueError("paired steps require a cumulative-cost delta")
            expected_relationship = (
                BuildStepRelationship.MATCHED
                if self.left_step.building == self.right_step.building
                else BuildStepRelationship.DIFFERENT
            )
            if self.relationship is not expected_relationship:
                raise ValueError("paired relationship does not match step identities")
        else:
            if any(
                value is not None
                for value in (
                    self.date_delta,
                    self.individual_cost_delta,
                    self.cumulative_cost_delta,
                )
            ):
                raise ValueError("unpaired steps cannot expose paired deltas")
            expected_relationship = (
                BuildStepRelationship.LEFT_ONLY
                if self.left_step is not None
                else BuildStepRelationship.RIGHT_ONLY
            )
            if self.relationship is not expected_relationship:
                raise ValueError("unpaired relationship does not match populated side")


@dataclass(frozen=True, slots=True)
class BuildPlanComparison:
    """Authoritative immutable right-minus-left comparison of accepted plans."""

    left_correlation_id: str | None
    right_correlation_id: str | None
    left_plan: BuildPlan
    right_plan: BuildPlan
    left_completion_date: object
    right_completion_date: object
    completion_date_delta: int
    left_step_count: int
    right_step_count: int
    step_count_delta: int
    left_final_cumulative_cost: ResourceCost
    right_final_cumulative_cost: ResourceCost
    final_cumulative_cost_delta: ResourceCost
    step_comparisons: tuple[BuildStepComparison, ...]
    common_buildings: tuple[BuildingKey, ...]
    left_only_actions: tuple[BuildStep, ...]
    right_only_actions: tuple[BuildStep, ...]
    status: BuildPlanComparisonStatus

    def __post_init__(self) -> None:
        normalized = tuple(self.step_comparisons)
        if tuple(item.comparison_position for item in normalized) != tuple(
            range(1, len(normalized) + 1)
        ):
            raise ValueError("comparison positions must be contiguous")
        object.__setattr__(self, "step_comparisons", normalized)
        object.__setattr__(self, "common_buildings", tuple(self.common_buildings))
        object.__setattr__(self, "left_only_actions", tuple(self.left_only_actions))
        object.__setattr__(self, "right_only_actions", tuple(self.right_only_actions))


@dataclass(frozen=True, slots=True)
class BuildPlanComparisonFailure:
    """Immutable expected comparison-unavailable state."""

    code: BuildPlanComparisonFailureCode
    message: str
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, BuildPlanComparisonFailureCode):
            raise TypeError("code must be BuildPlanComparisonFailureCode")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("failure message cannot be blank")


@dataclass(frozen=True, slots=True)
class BuildPlanComparisonOutcome:
    """Exactly one successful comparison or typed expected failure."""

    comparison: BuildPlanComparison | None = None
    failure: BuildPlanComparisonFailure | None = None

    def __post_init__(self) -> None:
        if (self.comparison is None) == (self.failure is None):
            raise ValueError("outcome requires exactly one comparison or failure")

    @property
    def is_ready(self) -> bool:
        return self.comparison is not None


def compare_accepted_build_plans(
    left: AcceptedBuildPlanInput | None,
    right: AcceptedBuildPlanInput | None,
) -> BuildPlanComparisonOutcome:
    """Compare two already accepted planner results without planning or I/O.

    All signed values use ``right - left``. Step alignment uses a deterministic
    longest-common-subsequence over complete ``BuildingKey`` values. Unmatched
    runs between common steps are paired chronologically as ``DIFFERENT`` and
    any remaining actions are emitted as side-only entries.
    """
    if left is None:
        return _failure(
            BuildPlanComparisonFailureCode.MISSING_LEFT_ACCEPTED_PLAN,
            "left accepted plan is required",
        )
    if right is None:
        return _failure(
            BuildPlanComparisonFailureCode.MISSING_RIGHT_ACCEPTED_PLAN,
            "right accepted plan is required",
        )
    if not isinstance(left, AcceptedBuildPlanInput):
        raise TypeError("left must be AcceptedBuildPlanInput or None")
    if not isinstance(right, AcceptedBuildPlanInput):
        raise TypeError("right must be AcceptedBuildPlanInput or None")

    left_plan = left.accepted_result.plan
    right_plan = right.accepted_result.plan
    left_error = _validate_plan(left_plan)
    if left_error is not None:
        return _failure(
            BuildPlanComparisonFailureCode.INVALID_LEFT_PLAN_DATA,
            left_error,
            left.correlation_id,
        )
    right_error = _validate_plan(right_plan)
    if right_error is not None:
        return _failure(
            BuildPlanComparisonFailureCode.INVALID_RIGHT_PLAN_DATA,
            right_error,
            right.correlation_id,
        )

    aligned = _align_steps(left_plan.steps, right_plan.steps)
    common = tuple(
        item.left_step.building
        for item in aligned
        if item.relationship is BuildStepRelationship.MATCHED
        and item.left_step is not None
    )
    left_only = tuple(
        item.left_step
        for item in aligned
        if item.relationship
        in (BuildStepRelationship.LEFT_ONLY, BuildStepRelationship.DIFFERENT)
        and item.left_step is not None
    )
    right_only = tuple(
        item.right_step
        for item in aligned
        if item.relationship
        in (BuildStepRelationship.RIGHT_ONLY, BuildStepRelationship.DIFFERENT)
        and item.right_step is not None
    )

    equivalent = (
        all(
            item.relationship is BuildStepRelationship.MATCHED
            and item.date_delta == 0
            and item.individual_cost_delta is not None
            and item.individual_cost_delta.is_zero()
            and item.cumulative_cost_delta is not None
            and item.cumulative_cost_delta.is_zero()
            for item in aligned
        )
        and len(left_plan.steps) == len(right_plan.steps)
        and left_plan.total_cost == right_plan.total_cost
        and left_plan.completion_date == right_plan.completion_date
    )

    comparison = BuildPlanComparison(
        left_correlation_id=left.correlation_id,
        right_correlation_id=right.correlation_id,
        left_plan=left_plan,
        right_plan=right_plan,
        left_completion_date=left_plan.completion_date,
        right_completion_date=right_plan.completion_date,
        completion_date_delta=(
            right_plan.completion_date.day_index - left_plan.completion_date.day_index
        ),
        left_step_count=left_plan.build_actions,
        right_step_count=right_plan.build_actions,
        step_count_delta=right_plan.build_actions - left_plan.build_actions,
        left_final_cumulative_cost=left_plan.total_cost,
        right_final_cumulative_cost=right_plan.total_cost,
        final_cumulative_cost_delta=right_plan.total_cost - left_plan.total_cost,
        step_comparisons=aligned,
        common_buildings=common,
        left_only_actions=left_only,
        right_only_actions=right_only,
        status=(
            BuildPlanComparisonStatus.EQUIVALENT
            if equivalent
            else BuildPlanComparisonStatus.DIFFERENT
        ),
    )
    return BuildPlanComparisonOutcome(comparison=comparison)


def _failure(
    code: BuildPlanComparisonFailureCode,
    message: str,
    correlation_id: str | None = None,
) -> BuildPlanComparisonOutcome:
    return BuildPlanComparisonOutcome(
        failure=BuildPlanComparisonFailure(code, message, correlation_id)
    )


def _validate_plan(plan: BuildPlan) -> str | None:
    if not isinstance(plan, BuildPlan):
        return "accepted result does not contain a BuildPlan"
    expected_cumulative = ResourceCost()
    for index, step in enumerate(plan.steps, start=1):
        if not isinstance(step, BuildStep):
            return f"plan step {index} is not a BuildStep"
        if step.step_number != index:
            return "plan step numbers must be contiguous and one-based"
        expected_cumulative = expected_cumulative + step.individual_cost
        if step.cumulative_cost != expected_cumulative:
            return f"plan step {index} has an invalid cumulative cost"
        if index > 1 and step.date.day_index < plan.steps[index - 2].date.day_index:
            return "plan steps must preserve chronological order"
    if plan.total_cost != expected_cumulative:
        return "plan total cost does not match cumulative construction cost"
    return None


def _align_steps(
    left_steps: tuple[BuildStep, ...],
    right_steps: tuple[BuildStep, ...],
) -> tuple[BuildStepComparison, ...]:
    matches = _lcs_matches(left_steps, right_steps)
    entries: list[tuple[BuildStep | None, BuildStep | None]] = []
    left_cursor = 0
    right_cursor = 0

    for left_match, right_match in (*matches, (len(left_steps), len(right_steps))):
        left_run = left_steps[left_cursor:left_match]
        right_run = right_steps[right_cursor:right_match]
        paired = min(len(left_run), len(right_run))
        entries.extend(zip(left_run[:paired], right_run[:paired]))
        entries.extend((step, None) for step in left_run[paired:])
        entries.extend((None, step) for step in right_run[paired:])

        if left_match < len(left_steps):
            entries.append((left_steps[left_match], right_steps[right_match]))
        left_cursor = left_match + 1
        right_cursor = right_match + 1

    return tuple(
        _step_comparison(position, left_step, right_step)
        for position, (left_step, right_step) in enumerate(entries, start=1)
    )


def _lcs_matches(
    left_steps: tuple[BuildStep, ...],
    right_steps: tuple[BuildStep, ...],
) -> tuple[tuple[int, int], ...]:
    left_ids = tuple(step.building for step in left_steps)
    right_ids = tuple(step.building for step in right_steps)
    rows = len(left_ids) + 1
    cols = len(right_ids) + 1
    lengths = [[0] * cols for _ in range(rows)]

    for left_index in range(len(left_ids) - 1, -1, -1):
        for right_index in range(len(right_ids) - 1, -1, -1):
            if left_ids[left_index] == right_ids[right_index]:
                lengths[left_index][right_index] = (
                    1 + lengths[left_index + 1][right_index + 1]
                )
            else:
                lengths[left_index][right_index] = max(
                    lengths[left_index + 1][right_index],
                    lengths[left_index][right_index + 1],
                )

    matches: list[tuple[int, int]] = []
    left_index = 0
    right_index = 0
    while left_index < len(left_ids) and right_index < len(right_ids):
        if left_ids[left_index] == right_ids[right_index]:
            matches.append((left_index, right_index))
            left_index += 1
            right_index += 1
        elif lengths[left_index + 1][right_index] >= lengths[left_index][right_index + 1]:
            left_index += 1
        else:
            right_index += 1
    return tuple(matches)


def _step_comparison(
    position: int,
    left_step: BuildStep | None,
    right_step: BuildStep | None,
) -> BuildStepComparison:
    if left_step is None:
        relationship = BuildStepRelationship.RIGHT_ONLY
    elif right_step is None:
        relationship = BuildStepRelationship.LEFT_ONLY
    elif left_step.building == right_step.building:
        relationship = BuildStepRelationship.MATCHED
    else:
        relationship = BuildStepRelationship.DIFFERENT

    both = left_step is not None and right_step is not None
    identity_matches = bool(
        both
        and left_step.building.faction == right_step.building.faction
        and left_step.building.sid == right_step.building.sid
    )
    level_matches = bool(
        both and left_step.building.level == right_step.building.level
    )
    return BuildStepComparison(
        comparison_position=position,
        left_step=left_step,
        right_step=right_step,
        relationship=relationship,
        date_delta=(
            right_step.date.day_index - left_step.date.day_index if both else None
        ),
        individual_cost_delta=(
            right_step.individual_cost - left_step.individual_cost if both else None
        ),
        cumulative_cost_delta=(
            right_step.cumulative_cost - left_step.cumulative_cost if both else None
        ),
        building_identity_matches=identity_matches,
        building_level_matches=level_matches,
    )
