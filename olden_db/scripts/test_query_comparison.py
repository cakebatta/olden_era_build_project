from __future__ import annotations

from olden_db.models import BuildingKey, ResourceCost
from olden_db.query import (
    PlanningQueryService,
    UnknownBuildingError,
    UnknownFactionError,
)
from olden_db.scenario import (
    InvalidStartingBuildingOverrideError,
    PlanningScenario,
    StartingBuildingOverride,
)


def main() -> None:
    service = PlanningQueryService.from_default_game_data()
    target = BuildingKey("undead", "Build_Tier_6", 1)
    wall = BuildingKey("undead", "Build_Wall", 1)

    identical = service.compare_plans(
        target.faction,
        target.sid,
        target.level,
        right_faction=target.faction,
        right_sid=target.sid,
        right_level=target.level,
    )
    if not identical.identical:
        raise RuntimeError("Identical canonical plans were not reported identical")
    if identical.action_delta != 0 or identical.completion_date_delta != 0:
        raise RuntimeError("Identical canonical plans produced nonzero deltas")
    if identical.resource_delta != ResourceCost():
        raise RuntimeError("Identical canonical plans produced a resource delta")
    if identical.added_buildings or identical.removed_buildings:
        raise RuntimeError("Identical canonical plans produced action differences")

    remove_wall = PlanningScenario(
        (StartingBuildingOverride(wall, False),)
    )
    canonical_vs_scenario = service.compare_plans(
        target.faction,
        target.sid,
        target.level,
        right_faction=target.faction,
        right_sid=target.sid,
        right_level=target.level,
        right_scenario=remove_wall,
    )
    if canonical_vs_scenario.action_delta <= 0:
        raise RuntimeError("Removing canonical Wall did not add actions")
    if canonical_vs_scenario.completion_date_delta <= 0:
        raise RuntimeError("Removing canonical Wall did not finish later")
    if wall not in canonical_vs_scenario.added_buildings:
        raise RuntimeError("Removed canonical Wall was not reported as added")

    add_target, add_prerequisite = _find_constructible_prerequisite(service)
    add_start = PlanningScenario(
        (StartingBuildingOverride(add_prerequisite, True),)
    )
    two_scenarios = service.compare_plans(
        target.faction,
        target.sid,
        target.level,
        left_scenario=remove_wall,
        right_faction=add_target.faction,
        right_sid=add_target.sid,
        right_level=add_target.level,
        right_scenario=add_start,
    )
    expected_left = service.generate_build_plan(
        target.faction,
        target.sid,
        target.level,
        scenario=remove_wall,
    )
    expected_right = service.generate_build_plan(
        add_target.faction,
        add_target.sid,
        add_target.level,
        scenario=add_start,
    )
    if two_scenarios.left_plan != expected_left:
        raise RuntimeError("Left scenario was not resolved independently")
    if two_scenarios.right_plan != expected_right:
        raise RuntimeError("Right scenario was not resolved independently")

    reverse = service.compare_plans(
        target.faction,
        target.sid,
        target.level,
        left_scenario=remove_wall,
        right_faction=target.faction,
        right_sid=target.sid,
        right_level=target.level,
    )
    if reverse.action_delta != -canonical_vs_scenario.action_delta:
        raise RuntimeError("Query comparison action symmetry failed")
    if reverse.completion_date_delta != -canonical_vs_scenario.completion_date_delta:
        raise RuntimeError("Query comparison date symmetry failed")
    if reverse.resource_delta != ResourceCost() - canonical_vs_scenario.resource_delta:
        raise RuntimeError("Query comparison resource symmetry failed")
    if reverse.added_buildings != canonical_vs_scenario.removed_buildings:
        raise RuntimeError("Query comparison added-building symmetry failed")
    if reverse.removed_buildings != canonical_vs_scenario.added_buildings:
        raise RuntimeError("Query comparison removed-building symmetry failed")
    if reverse.identical != canonical_vs_scenario.identical:
        raise RuntimeError("Query comparison identical symmetry failed")

    repeated = service.compare_plans(
        target.faction,
        target.sid,
        target.level,
        right_faction=target.faction,
        right_sid=target.sid,
        right_level=target.level,
        right_scenario=remove_wall,
    )
    if repeated != canonical_vs_scenario:
        raise RuntimeError("Repeated Query Layer comparison was not deterministic")

    _check_errors(service, target)

    print("Query Layer comparison validation completed successfully.")
    print("Identical canonical plans produced zero deltas.")
    print("Canonical and scenario plans compared through the public Query Layer.")
    print("Independent left and right scenarios were resolved correctly.")
    print("Comparison symmetry and determinism were preserved.")
    print("Existing Query Layer errors propagated through comparison.")


def _find_constructible_prerequisite(
    service: PlanningQueryService,
) -> tuple[BuildingKey, BuildingKey]:
    for faction in service.list_factions():
        for sid in service.list_buildings(faction):
            for level in service.list_building_levels(faction, sid):
                target = service.get_building(faction, sid, level)
                canonical_plan = service.generate_build_plan(
                    faction,
                    sid,
                    level,
                )
                for prerequisite in target.prerequisites:
                    if prerequisite in canonical_plan.order:
                        return target.key, prerequisite
    raise RuntimeError("No constructible direct prerequisite was found")


def _check_errors(
    service: PlanningQueryService,
    target: BuildingKey,
) -> None:
    try:
        service.compare_plans(
            "not_a_faction",
            target.sid,
            target.level,
            right_faction=target.faction,
            right_sid=target.sid,
            right_level=target.level,
        )
    except UnknownFactionError:
        pass
    else:
        raise RuntimeError("Unknown left faction did not propagate")

    try:
        service.compare_plans(
            target.faction,
            "not_a_building",
            1,
            right_faction=target.faction,
            right_sid=target.sid,
            right_level=target.level,
        )
    except UnknownBuildingError:
        pass
    else:
        raise RuntimeError("Unknown left building did not propagate")

    invalid = PlanningScenario(
        (
            StartingBuildingOverride(
                BuildingKey("nature", "Build_Wall", 1),
                True,
            ),
        )
    )
    try:
        service.compare_plans(
            target.faction,
            target.sid,
            target.level,
            right_faction=target.faction,
            right_sid=target.sid,
            right_level=target.level,
            right_scenario=invalid,
        )
    except InvalidStartingBuildingOverrideError:
        pass
    else:
        raise RuntimeError("Invalid right scenario did not propagate")


if __name__ == "__main__":
    main()
