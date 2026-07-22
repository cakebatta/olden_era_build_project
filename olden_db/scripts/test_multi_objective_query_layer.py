from __future__ import annotations

from dataclasses import FrozenInstanceError

from olden_db.models import ResourceCost
from olden_db.objective_planning import (
    BuildingCompletionObjective,
    ObjectivePlanningFailure,
    ObjectiveSet,
    TownPlanningRequest,
    TownState,
)
from olden_db.objective_query_models import MultiObjectivePlanningResultView
from olden_db.query import PlanningQueryService


def assert_raises(exc_type, fn) -> None:
    try:
        fn()
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__}")


def main() -> None:
    q = PlanningQueryService.from_default_game_data()
    faction = next(
        faction
        for faction in q.list_factions()
        if len(
            [
                key
                for key, building in q._data.cities.city(faction).buildings.items()
                if not building.constructed_on_start
            ]
        ) >= 2
    )
    city = q._data.cities.city(faction)
    targets = tuple(
        key
        for key, building in sorted(city.buildings.items())
        if not building.constructed_on_start
    )

    request = TownPlanningRequest(
        TownState(faction),
        ObjectiveSet(
            (
                BuildingCompletionObjective(targets[-1]),
                BuildingCompletionObjective(targets[0]),
            )
        ),
    )

    view_a = q.generate_objective_plan_view(request)
    view_b = q.generate_objective_plan_view(request)
    assert isinstance(view_a, MultiObjectivePlanningResultView)
    assert view_a == view_b
    assert all(item.display_name.strip() for item in view_a.summary.objectives)
    assert tuple(item.objective for item in view_a.objective_completions) == (
        view_a.summary.objectives
    )
    assert tuple(item.objective for item in view_a.prerequisite_provenance) == (
        view_a.summary.objectives
    )

    for step in view_a.build_steps:
        assert step.display_name == q.get_building_display_name(step.building)
        assert step.resource_balance_before - step.resource_cost == (
            step.resource_balance_after
        )
        assert step.income_change == city.buildings[step.building].income
        for objective in step.required_by_objectives:
            matching = next(
                item
                for item in view_a.prerequisite_provenance
                if item.objective == objective
            )
            assert step.building in matching.required_buildings

    if view_a.build_steps:
        assert view_a.build_steps[-1].resource_balance_after == ResourceCost()
        assert_raises(
            FrozenInstanceError,
            lambda: setattr(view_a.build_steps[0], "display_name", "changed"),
        )

    raw = q.generate_objective_plan(request)
    assert not isinstance(raw, ObjectivePlanningFailure)
    assert raw.plan.total_cost == view_a.summary.total_cost
    assert raw.plan.order == tuple(step.building for step in view_a.build_steps)

    one = BuildingCompletionObjective(targets[-1])
    one_request = TownPlanningRequest(TownState(faction), ObjectiveSet((one,)))
    one_view = q.generate_objective_plan_view(one_request)
    legacy = q.generate_planner_result(
        faction,
        one.building.sid,
        one.building.level,
    )
    assert isinstance(one_view, MultiObjectivePlanningResultView)
    assert one_view.summary.total_cost == legacy.plan.total_cost
    assert tuple(step.building for step in one_view.build_steps) == legacy.plan.order

    print("PASS: immutable Query Layer view contracts")
    print("PASS: localized display names use Query Layer ownership")
    print("PASS: objective completion projection")
    print("PASS: bidirectional prerequisite provenance")
    print("PASS: deterministic build-step explanations")
    print("PASS: resource and income explanation facts")
    print("PASS: existing single-target Query Layer compatibility")


if __name__ == "__main__":
    main()
