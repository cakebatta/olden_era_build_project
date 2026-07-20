from __future__ import annotations

from olden_db.models import BuildingKey, ResourceCost
from olden_db.planner import (
    BuildPlan,
    BuildStep,
    DailyConstructionCost,
    GameDate,
    PlannerResult,
)


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def make_result() -> PlannerResult:
    key = BuildingKey("test", "hall", 1)
    date = GameDate(1, 1, 2)
    cost = ResourceCost(gold=500, wood=5)
    step = BuildStep(1, date, key, cost, cost)
    plan = BuildPlan("test", key, 1, (step,), cost, GameDate(1, 1, 1))
    return PlannerResult(
        plan,
        daily_construction_schedule=(DailyConstructionCost(date, key, cost),),
    )


def test_summary_values_match_accepted_result_contract() -> None:
    result = make_result()
    require(result.plan.build_actions == 1, "Step count mismatch")
    require(result.plan.completion_date == GameDate(1, 1, 2), "Completion mismatch")
    require(result.plan.total_cost == ResourceCost(gold=500, wood=5), "Total cost mismatch")
    require(len(result.daily_construction_schedule) == 1, "Schedule row missing")
    row = result.daily_construction_schedule[0]
    require(row.date == result.plan.steps[0].date, "Schedule date mismatch")
    require(row.cost == result.plan.steps[0].individual_cost, "Schedule cost mismatch")


def test_daily_schedule_is_deterministic() -> None:
    require(make_result() == make_result(), "Repeated accepted result must be deterministic")


def main() -> None:
    tests = [test_summary_values_match_accepted_result_contract, test_daily_schedule_is_deterministic]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} UI-007 summary integration checks")


if __name__ == "__main__":
    main()
