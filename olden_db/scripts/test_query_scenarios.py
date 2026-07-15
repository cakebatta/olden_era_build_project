from __future__ import annotations

from olden_db.models import BuildingKey
from olden_db.query import PlanningQueryService
from olden_db.scenario import (
    InvalidStartingBuildingOverrideError,
    PlanningScenario,
    StartingBuildingOverride,
)


def main() -> None:
    service = PlanningQueryService.from_default_game_data()

    target = BuildingKey("undead", "Build_Tier_6", 1)
    wall = BuildingKey("undead", "Build_Wall", 1)

    canonical_plan = service.generate_build_plan(
        target.faction,
        target.sid,
        target.level,
    )
    canonical_cost = service.get_cumulative_cost(
        target.faction,
        target.sid,
        target.level,
    )
    canonical_orders = service.enumerate_build_orders(
        target.faction,
        target.sid,
        target.level,
    )

    empty = PlanningScenario()
    empty_plan = service.generate_build_plan(
        target.faction,
        target.sid,
        target.level,
        scenario=empty,
    )
    empty_cost = service.get_cumulative_cost(
        target.faction,
        target.sid,
        target.level,
        scenario=empty,
    )
    empty_orders = service.enumerate_build_orders(
        target.faction,
        target.sid,
        target.level,
        scenario=empty,
    )
    if (empty_plan, empty_cost, empty_orders) != (
        canonical_plan,
        canonical_cost,
        canonical_orders,
    ):
        raise RuntimeError("Empty scenario did not preserve canonical behavior")

    remove_wall = PlanningScenario(
        (StartingBuildingOverride(wall, False),)
    )
    wall_plan = service.generate_build_plan(
        target.faction,
        target.sid,
        target.level,
        scenario=remove_wall,
    )
    wall_cost = service.get_cumulative_cost(
        target.faction,
        target.sid,
        target.level,
        scenario=remove_wall,
    )
    wall_orders = service.enumerate_build_orders(
        target.faction,
        target.sid,
        target.level,
        scenario=remove_wall,
    )
    if wall not in wall_plan.order:
        raise RuntimeError("Removed canonical Wall was not constructed")
    if wall_plan.total_cost != wall_cost:
        raise RuntimeError("Scenario cost query disagreed with BuildPlan.total_cost")
    if not wall_orders or wall_plan.order != wall_orders[0]:
        raise RuntimeError("Scenario plan and build-order query disagreed")

    repeated = service.generate_build_plan(
        target.faction,
        target.sid,
        target.level,
        scenario=remove_wall,
    )
    if repeated != wall_plan:
        raise RuntimeError("Repeated scenario planning was not deterministic")

    statuses = service.get_prerequisite_statuses(
        target.faction,
        target.sid,
        target.level,
        scenario=remove_wall,
    )
    wall_status = next(
        (status for status in statuses if status.building.key == wall),
        None,
    )
    if wall_status is None:
        raise RuntimeError("Wall prerequisite status was not returned")
    if wall_status.available_at_start:
        raise RuntimeError("Removed Wall was still reported available at start")
    if not wall_status.overridden:
        raise RuntimeError("Removed Wall was not reported as overridden")

    add_key = _find_constructible_direct_prerequisite(service)
    add_target, prerequisite = add_key
    add_scenario = PlanningScenario(
        (StartingBuildingOverride(prerequisite, True),)
    )
    base_plan = service.generate_build_plan(
        add_target.faction,
        add_target.sid,
        add_target.level,
    )
    scenario_plan = service.generate_build_plan(
        add_target.faction,
        add_target.sid,
        add_target.level,
        scenario=add_scenario,
    )
    if prerequisite not in base_plan.order:
        raise RuntimeError("Selected prerequisite was not canonically constructed")
    if prerequisite in scenario_plan.order:
        raise RuntimeError("Added starting building remained a construction action")

    add_statuses = service.get_prerequisite_statuses(
        add_target.faction,
        add_target.sid,
        add_target.level,
        scenario=add_scenario,
    )
    added_status = next(
        status
        for status in add_statuses
        if status.building.key == prerequisite
    )
    if not added_status.available_at_start or not added_status.overridden:
        raise RuntimeError("Added starting building status was incorrect")

    _check_invalid_scenario(service, target)

    print("Scenario-aware Query Layer validation completed successfully.")
    print("Empty scenario matched canonical plan, cost, and build orders.")
    print("Removing canonical Wall changed construction requirements correctly.")
    print("Adding a noncanonical starting prerequisite stopped construction at it.")
    print("Prerequisite statuses reflected effective and overridden values.")
    print("Scenario plans, costs, and build orders remained deterministic and consistent.")


def _find_constructible_direct_prerequisite(
    service: PlanningQueryService,
) -> tuple[BuildingKey, BuildingKey]:
    for faction in service.list_factions():
        for sid in service.list_buildings(faction):
            for level in service.list_building_levels(faction, sid):
                target = service.get_building(faction, sid, level)
                for prerequisite in target.prerequisites:
                    building = service.get_building(
                        prerequisite.faction,
                        prerequisite.sid,
                        prerequisite.level,
                    )
                    if building.constructed_on_start:
                        continue
                    base_plan = service.generate_build_plan(
                        target.key.faction,
                        target.key.sid,
                        target.key.level,
                    )
                    if prerequisite in base_plan.order:
                        return target.key, prerequisite
    raise RuntimeError("No constructible direct prerequisite was found")


def _check_invalid_scenario(
    service: PlanningQueryService,
    target: BuildingKey,
) -> None:
    invalid = PlanningScenario(
        (
            StartingBuildingOverride(
                BuildingKey("nature", "Build_Wall", 1),
                True,
            ),
        )
    )
    try:
        service.generate_build_plan(
            target.faction,
            target.sid,
            target.level,
            scenario=invalid,
        )
    except InvalidStartingBuildingOverrideError:
        pass
    else:
        raise RuntimeError("Cross-faction scenario was not rejected")


if __name__ == "__main__":
    main()
