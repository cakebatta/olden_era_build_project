from __future__ import annotations

from olden_db.comparison import compare_build_plans
from olden_db.models import BuildingKey, ResourceCost
from olden_db.query import PlanningQueryService
from olden_db.scenario import PlanningScenario, StartingBuildingOverride


def main() -> None:
    service = PlanningQueryService.from_default_game_data()

    target = BuildingKey("undead", "Build_Tier_6", 1)
    wall = BuildingKey("undead", "Build_Wall", 1)

    canonical = service.generate_build_plan(
        target.faction,
        target.sid,
        target.level,
    )
    canonical_snapshot = canonical

    identical = compare_build_plans(canonical, canonical)
    if not identical.identical:
        raise RuntimeError("Identical plans were not reported as identical")
    if identical.action_delta != 0 or identical.completion_date_delta != 0:
        raise RuntimeError("Identical plans produced nonzero scalar deltas")
    if identical.resource_delta != ResourceCost():
        raise RuntimeError("Identical plans produced a nonzero resource delta")
    if identical.added_buildings or identical.removed_buildings:
        raise RuntimeError("Identical plans produced building differences")

    remove_wall = PlanningScenario(
        (StartingBuildingOverride(wall, False),)
    )
    wall_plan = service.generate_build_plan(
        target.faction,
        target.sid,
        target.level,
        scenario=remove_wall,
    )
    wall_snapshot = wall_plan

    canonical_to_wall = compare_build_plans(canonical, wall_plan)
    if canonical_to_wall.identical:
        raise RuntimeError("Different canonical and Wall plans were identical")
    if canonical_to_wall.action_delta <= 0:
        raise RuntimeError("Removing Wall did not increase action count")
    if canonical_to_wall.completion_date_delta <= 0:
        raise RuntimeError("Removing Wall did not delay completion")
    if wall not in canonical_to_wall.added_buildings:
        raise RuntimeError("Wall was not reported as an added action")
    if canonical_to_wall.resource_delta == ResourceCost():
        raise RuntimeError("Removing Wall produced no resource difference")

    reverse = compare_build_plans(wall_plan, canonical)
    _assert_symmetric(canonical_to_wall, reverse)

    add_target, added_start = _find_constructible_prerequisite(service)
    add_canonical = service.generate_build_plan(
        add_target.faction,
        add_target.sid,
        add_target.level,
    )
    add_scenario = PlanningScenario(
        (StartingBuildingOverride(added_start, True),)
    )
    add_plan = service.generate_build_plan(
        add_target.faction,
        add_target.sid,
        add_target.level,
        scenario=add_scenario,
    )
    added_start_comparison = compare_build_plans(add_canonical, add_plan)
    if added_start_comparison.action_delta >= 0:
        raise RuntimeError("Added starting building did not reduce actions")
    if added_start_comparison.completion_date_delta > 0:
        raise RuntimeError("Added starting building made completion later")
    if added_start not in added_start_comparison.removed_buildings:
        raise RuntimeError("Starting building was not reported as removed")
    if not _has_negative_resource(added_start_comparison.resource_delta):
        raise RuntimeError("Added starting building did not reduce any resource")

    repeated = compare_build_plans(canonical, wall_plan)
    if repeated != canonical_to_wall:
        raise RuntimeError("Repeated comparisons were not deterministic")

    if canonical != canonical_snapshot or wall_plan != wall_snapshot:
        raise RuntimeError("Plan comparison mutated an input plan")

    print("Plan comparison validation completed successfully.")
    print("Identical plans produced zero deltas and no action differences.")
    print("Canonical-to-scenario deltas followed right-minus-left semantics.")
    print("Added and removed construction actions were reported deterministically.")
    print("Comparison symmetry, determinism, and input immutability were preserved.")


def _assert_symmetric(forward, reverse) -> None:
    if reverse.action_delta != -forward.action_delta:
        raise RuntimeError("Action delta did not reverse sign")
    if reverse.completion_date_delta != -forward.completion_date_delta:
        raise RuntimeError("Completion-date delta did not reverse sign")
    if reverse.resource_delta != ResourceCost() - forward.resource_delta:
        raise RuntimeError("Resource delta did not reverse sign")
    if reverse.added_buildings != forward.removed_buildings:
        raise RuntimeError("Added buildings did not swap with removed buildings")
    if reverse.removed_buildings != forward.added_buildings:
        raise RuntimeError("Removed buildings did not swap with added buildings")
    if reverse.identical != forward.identical:
        raise RuntimeError("Identical status changed when comparison was reversed")


def _find_constructible_prerequisite(
    service: PlanningQueryService,
) -> tuple[BuildingKey, BuildingKey]:
    for faction in service.list_factions():
        for sid in service.list_buildings(faction):
            for level in service.list_building_levels(faction, sid):
                target = service.get_building(faction, sid, level)
                canonical = service.generate_build_plan(faction, sid, level)
                for prerequisite in target.prerequisites:
                    if prerequisite in canonical.order:
                        return target.key, prerequisite
    raise RuntimeError("No canonically constructed prerequisite was found")


def _has_negative_resource(cost: ResourceCost) -> bool:
    return any(value < 0 for value in cost.as_dict().values())


if __name__ == "__main__":
    main()
