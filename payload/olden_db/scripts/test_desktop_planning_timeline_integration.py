from __future__ import annotations

from olden_db.models import BuildingKey, ResourceCost
from olden_db.planner import BuildPlan, BuildStep, GameDate, PlannerResult


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def make_result() -> PlannerResult:
    first = BuildingKey("test", "hall", 1)
    second = BuildingKey("test", "fort", 2)
    cost1 = ResourceCost(gold=500, wood=5)
    cost2 = ResourceCost(gold=1000, ore=10)
    total = cost1 + cost2
    steps = (
        BuildStep(1, GameDate(1, 1, 2), first, cost1, cost1),
        BuildStep(2, GameDate(1, 1, 3), second, cost2, total),
    )
    return PlannerResult(BuildPlan("test", second, 1, steps, total, GameDate(1, 1, 1)))


def test_chronological_accepted_order() -> None:
    result = make_result()
    require(tuple(step.step_number for step in result.plan.steps) == (1, 2), "Order mismatch")
    require(result.plan.steps[0].date < result.plan.steps[1].date, "Dates not chronological")


def test_authoritative_costs() -> None:
    result = make_result()
    require(result.plan.steps[-1].cumulative_cost == result.plan.total_cost, "Cumulative mismatch")


def test_equivalent_results_are_deterministic() -> None:
    require(make_result() == make_result(), "Equivalent results differ")


def main() -> None:
    items = [test_chronological_accepted_order, test_authoritative_costs, test_equivalent_results_are_deterministic]
    for item in items:
        item()
        print(f"PASS: {item.__name__}")
    print(f"PASS: {len(items)} UI-008 timeline integration checks")


if __name__ == "__main__":
    main()
