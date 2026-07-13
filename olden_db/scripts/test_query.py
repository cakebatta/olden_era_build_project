from __future__ import annotations

from olden_db.database import load_default_game_data
from olden_db.models import ResourceCost
from olden_db.query import (
    PlanningQueryService,
    UnknownBuildingError,
    UnknownFactionError,
)


def main() -> None:
    service = PlanningQueryService(load_default_game_data())
    target = _representative_target(service)
    faction, sid, level = (
        target.key.faction,
        target.key.sid,
        target.key.level,
    )

    if service.get_building(faction, sid, level) != target:
        raise RuntimeError("Building query returned the wrong object")

    prerequisites = service.get_prerequisites(faction, sid, level)
    expected = tuple(
        sorted(target.prerequisites, key=lambda key: (key.sid, key.level))
    )
    if tuple(item.key for item in prerequisites) != expected:
        raise RuntimeError("Prerequisites were incorrect or non-deterministic")

    first_plan = service.generate_build_plan(faction, sid, level)
    second_plan = service.generate_build_plan(faction, sid, level)
    if first_plan != second_plan:
        raise RuntimeError("Repeated plan queries returned different results")

    cost = service.get_cumulative_cost(faction, sid, level)
    if not isinstance(cost, ResourceCost) or cost != first_plan.total_cost:
        raise RuntimeError("Cumulative cost did not match the returned plan")

    first_orders = service.enumerate_build_orders(faction, sid, level)
    second_orders = service.enumerate_build_orders(faction, sid, level)
    if not first_orders or first_orders != second_orders:
        raise RuntimeError("Build-order results were empty or non-deterministic")
    if first_plan.order != first_orders[0]:
        raise RuntimeError("Plan did not use the first deterministic legal order")

    _check_errors(service)

    print("Query Layer validation completed successfully.")
    print(f"Representative target: {faction}/{sid} level {level}")
    print(f"Direct prerequisites returned: {len(prerequisites)}")
    print(f"Legal build orders returned: {len(first_orders)}")
    print(f"Build actions in plan: {first_plan.build_actions}")
    print("Repeated queries returned identical structured domain objects.")


def _representative_target(service: PlanningQueryService):
    buildings = sorted(
        (
            building
            for city in service.data.cities.cities.values()
            for building in city.buildings.values()
            if building.prerequisites
        ),
        key=lambda item: (
            item.key.faction,
            item.key.sid,
            item.key.level,
        ),
    )
    if not buildings:
        raise RuntimeError("No building with prerequisites was found")
    return buildings[0]


def _check_errors(service: PlanningQueryService) -> None:
    try:
        service.get_building("not_a_faction", "missing", 1)
    except UnknownFactionError:
        pass
    else:
        raise RuntimeError("Unknown faction did not raise UnknownFactionError")

    faction = sorted(service.data.cities.cities)[0]
    try:
        service.get_building(faction, "not_a_building", 1)
    except UnknownBuildingError:
        pass
    else:
        raise RuntimeError("Unknown building did not raise UnknownBuildingError")


if __name__ == "__main__":
    main()
