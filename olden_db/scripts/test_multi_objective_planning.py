from __future__ import annotations

from dataclasses import FrozenInstanceError

from olden_db.objective_planning import (
    BuildingCompletionObjective,
    CrossTownObjectiveError,
    EmptyObjectiveSetError,
    MultiObjectivePlannerResult,
    ObjectiveSet,
    TownPlanningRequest,
    TownState,
)
from olden_db.planner import GameDate
from olden_db.query import PlanningQueryService
from olden_db.scenario import PlanningScenario


def assert_raises(exc_type, fn) -> None:
    try:
        fn()
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__}")


def main() -> None:
    q = PlanningQueryService.from_default_game_data()

    faction = next(
        f for f in q.list_factions()
        if len(q._data.cities.city(f).buildings) >= 2
    )
    city = q._data.cities.city(faction)
    targets = tuple(
        key for key in sorted(city.buildings)
        if not city.buildings[key].constructed_on_start
    )
    first = BuildingCompletionObjective(targets[0])
    second = BuildingCompletionObjective(targets[-1])

    normalized = ObjectiveSet((second, first, second))
    assert normalized.objectives == tuple(sorted({first, second}))
    assert ObjectiveSet((first, second)) == ObjectiveSet((second, first))
    assert_raises(FrozenInstanceError, lambda: setattr(first, "building", targets[1]))
    assert_raises(FrozenInstanceError, lambda: setattr(normalized, "objectives", (first,)))

    empty = TownPlanningRequest(TownState(faction), ObjectiveSet(()))
    assert_raises(EmptyObjectiveSetError, lambda: q.generate_objective_plan(empty))

    other_faction = next(f for f in q.list_factions() if f != faction)
    other_key = next(iter(sorted(q._data.cities.city(other_faction).buildings)))
    cross = TownPlanningRequest(
        TownState(faction),
        ObjectiveSet((BuildingCompletionObjective(other_key),)),
    )
    assert_raises(CrossTownObjectiveError, lambda: q.generate_objective_plan(cross))

    request_a = TownPlanningRequest(
        TownState(faction, GameDate(1, 1, 1), PlanningScenario()),
        ObjectiveSet((first, second)),
    )
    request_b = TownPlanningRequest(
        request_a.town_state,
        ObjectiveSet((second, first, first)),
    )
    result_a = q.generate_objective_plan(request_a)
    result_b = q.generate_objective_plan(request_b)
    assert isinstance(result_a, MultiObjectivePlannerResult)
    assert result_a.plan.order == result_b.plan.order
    assert result_a.plan.total_cost == result_b.plan.total_cost
    assert len(result_a.plan.order) == len(set(result_a.plan.order))
    assert tuple(x.building for x in result_a.step_provenance) == result_a.plan.order

    one = q.generate_objective_plan(
        TownPlanningRequest(TownState(faction), ObjectiveSet((first,)))
    )
    legacy_plan = q.generate_build_plan(
        faction, first.building.sid, first.building.level
    )
    legacy_result = q.generate_planner_result(
        faction, first.building.sid, first.building.level
    )
    assert isinstance(one, MultiObjectivePlannerResult)
    assert one.plan == legacy_plan
    assert one.plan == legacy_result.plan

    print("PASS: immutable contracts")
    print("PASS: duplicate normalization")
    print("PASS: deterministic ordering")
    print("PASS: validation separation")
    print("PASS: integrated scheduling")
    print("PASS: one-objective compatibility")


if __name__ == "__main__":
    main()
