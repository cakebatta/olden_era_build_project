from __future__ import annotations

from dataclasses import FrozenInstanceError

from olden_db.comparison import (
    AcceptedBuildPlanInput,
    BuildPlanComparisonFailureCode,
    BuildPlanComparisonStatus,
    BuildStepRelationship,
    compare_accepted_build_plans,
)
from olden_db.models import BuildingKey, ResourceCost
from olden_db.planner import BuildPlan, BuildStep, GameDate, PlannerResult
from olden_db.query import PlanningQueryService


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def step(
    number: int,
    sid: str,
    level: int,
    day: int,
    cost: ResourceCost,
    cumulative: ResourceCost,
) -> BuildStep:
    return BuildStep(
        step_number=number,
        date=GameDate.from_day_index(day),
        building=BuildingKey("test", sid, level),
        individual_cost=cost,
        cumulative_cost=cumulative,
    )


def plan(*steps: BuildStep, starting_day: int = 0) -> BuildPlan:
    total = steps[-1].cumulative_cost if steps else ResourceCost()
    target = (
        steps[-1].building
        if steps
        else BuildingKey("test", "already_available", 1)
    )
    return BuildPlan(
        faction="test",
        target=target,
        order_number=1,
        steps=tuple(steps),
        total_cost=total,
        starting_date=GameDate.from_day_index(starting_day),
    )


def accepted(value: BuildPlan, correlation: str) -> AcceptedBuildPlanInput:
    return AcceptedBuildPlanInput(PlannerResult(value), correlation)


def test_identical_and_immutable() -> None:
    gold = ResourceCost(gold=100)
    value = plan(step(1, "hall", 1, 0, gold, gold))
    outcome = compare_accepted_build_plans(accepted(value, "left"), accepted(value, "right"))
    require(outcome.is_ready, "identical comparison unavailable")
    result = outcome.comparison
    require(result is not None, "comparison absent")
    require(result.status is BuildPlanComparisonStatus.EQUIVALENT, "not equivalent")
    require(result.completion_date_delta == 0, "date delta changed")
    require(result.step_count_delta == 0, "step delta changed")
    require(result.final_cumulative_cost_delta.is_zero(), "cost delta changed")
    require(
        tuple(item.relationship for item in result.step_comparisons)
        == (BuildStepRelationship.MATCHED,),
        "identical alignment changed",
    )
    try:
        result.step_count_delta = 5  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("comparison contract is mutable")


def test_divergence_repeated_upgrades_and_exclusive_order() -> None:
    a = ResourceCost(gold=10)
    b = ResourceCost(gold=20, wood=1)
    c = ResourceCost(gold=30)
    left = plan(
        step(1, "hall", 1, 0, a, a),
        step(2, "guild", 1, 1, b, a + b),
        step(3, "hall", 2, 2, c, a + b + c),
    )
    right = plan(
        step(1, "hall", 1, 0, a, a),
        step(2, "market", 1, 2, c, a + c),
        step(3, "hall", 2, 3, b, a + c + b),
    )
    result = compare_accepted_build_plans(
        accepted(left, "L"), accepted(right, "R")
    ).comparison
    require(result is not None, "divergent comparison unavailable")
    require(
        tuple(item.relationship for item in result.step_comparisons)
        == (
            BuildStepRelationship.MATCHED,
            BuildStepRelationship.DIFFERENT,
            BuildStepRelationship.MATCHED,
        ),
        "divergence alignment changed",
    )
    require(
        tuple(item.building.sid for item in result.left_only_actions) == ("guild",),
        "left-only ordering changed",
    )
    require(
        tuple(item.building.sid for item in result.right_only_actions) == ("market",),
        "right-only ordering changed",
    )
    require(
        result.common_buildings
        == (
            BuildingKey("test", "hall", 1),
            BuildingKey("test", "hall", 2),
        ),
        "repeated upgrade identities not preserved",
    )


def test_empty_and_signed_deltas() -> None:
    empty = plan(starting_day=0)
    gold = ResourceCost(gold=100, ore=2)
    nonempty = plan(step(1, "hall", 1, 3, gold, gold))
    result = compare_accepted_build_plans(
        accepted(empty, "L"), accepted(nonempty, "R")
    ).comparison
    require(result is not None, "empty comparison unavailable")
    require(result.completion_date_delta == 3, "date sign convention changed")
    require(result.step_count_delta == 1, "step sign convention changed")
    require(result.final_cumulative_cost_delta == gold, "cost sign convention changed")
    require(
        result.step_comparisons[0].relationship is BuildStepRelationship.RIGHT_ONLY,
        "empty alignment changed",
    )

    both_empty = compare_accepted_build_plans(
        accepted(empty, "L"), accepted(empty, "R")
    ).comparison
    require(
        both_empty is not None
        and both_empty.status is BuildPlanComparisonStatus.EQUIVALENT,
        "empty plans are not equivalent",
    )


def test_swap_and_determinism() -> None:
    a = ResourceCost(gold=10)
    b = ResourceCost(gold=30)
    left = plan(step(1, "hall", 1, 0, a, a))
    right = plan(step(1, "hall", 1, 2, b, b))
    forward = compare_accepted_build_plans(
        accepted(left, "L"), accepted(right, "R")
    ).comparison
    repeated = compare_accepted_build_plans(
        accepted(left, "L"), accepted(right, "R")
    ).comparison
    reverse = compare_accepted_build_plans(
        accepted(right, "R"), accepted(left, "L")
    ).comparison
    require(forward == repeated, "comparison is nondeterministic")
    require(forward is not None and reverse is not None, "swap unavailable")
    require(
        reverse.completion_date_delta == -forward.completion_date_delta,
        "date delta did not reverse",
    )
    require(
        reverse.step_count_delta == -forward.step_count_delta,
        "step delta did not reverse",
    )
    require(
        reverse.final_cumulative_cost_delta
        == ResourceCost() - forward.final_cumulative_cost_delta,
        "resource delta did not reverse",
    )


def test_typed_missing_failures() -> None:
    empty = accepted(plan(), "R")
    left_missing = compare_accepted_build_plans(None, empty)
    right_missing = compare_accepted_build_plans(empty, None)
    require(
        left_missing.failure is not None
        and left_missing.failure.code
        is BuildPlanComparisonFailureCode.MISSING_LEFT_ACCEPTED_PLAN,
        "left missing failure changed",
    )
    require(
        right_missing.failure is not None
        and right_missing.failure.code
        is BuildPlanComparisonFailureCode.MISSING_RIGHT_ACCEPTED_PLAN,
        "right missing failure changed",
    )


def test_public_query_access_and_no_regeneration() -> None:
    service = object.__new__(PlanningQueryService)
    left = accepted(plan(), "L")
    right = accepted(plan(), "R")
    outcome = service.compare_accepted_build_plans(left, right)
    require(outcome.is_ready, "public accepted-plan comparison unavailable")


def main() -> None:
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} build plan comparison service checks")


if __name__ == "__main__":
    main()
