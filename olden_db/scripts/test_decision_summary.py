from __future__ import annotations

from olden_db.comparison import compare_build_plans
from olden_db.constants import RESOURCE_NAMES
from olden_db.database import load_default_game_data
from olden_db.decision_summary import (
    ActionDeltaObservation,
    BuildingAddedObservation,
    BuildingRemovedObservation,
    CompletionDeltaObservation,
    PlansDifferObservation,
    PlansIdenticalObservation,
    ResourceDeltaObservation,
    summarize_plan_comparison,
)
from olden_db.graph import build_dependency_graph, iter_topological_orders
from olden_db.models import BuildingKey
from olden_db.planner import plan_build_order
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
    identical_comparison = compare_build_plans(canonical, canonical)
    identical_summary = summarize_plan_comparison(identical_comparison)

    if identical_summary.comparison is not identical_comparison:
        raise RuntimeError("Summary did not retain the source comparison")
    if identical_summary.observations != (PlansIdenticalObservation(),):
        raise RuntimeError(
            "Identical comparison did not produce exactly one identity observation"
        )

    remove_wall = PlanningScenario(
        (StartingBuildingOverride(wall, False),)
    )
    wall_plan = service.generate_build_plan(
        target.faction,
        target.sid,
        target.level,
        scenario=remove_wall,
    )
    forward_comparison = compare_build_plans(canonical, wall_plan)
    forward_snapshot = forward_comparison
    canonical_snapshot = canonical
    wall_snapshot = wall_plan

    forward = summarize_plan_comparison(forward_comparison)
    repeated = summarize_plan_comparison(forward_comparison)
    if forward != repeated:
        raise RuntimeError("Repeated summary generation was not deterministic")
    _check_forward_summary(forward, wall)

    reverse_comparison = compare_build_plans(wall_plan, canonical)
    reverse = summarize_plan_comparison(reverse_comparison)
    _check_reversed_summary(forward, reverse)

    add_target, added_start = _find_constructible_prerequisite(service)
    add_canonical = service.generate_build_plan(
        add_target.faction,
        add_target.sid,
        add_target.level,
    )
    add_plan = service.generate_build_plan(
        add_target.faction,
        add_target.sid,
        add_target.level,
        scenario=PlanningScenario(
            (StartingBuildingOverride(added_start, True),)
        ),
    )
    removed_summary = summarize_plan_comparison(
        compare_build_plans(add_canonical, add_plan)
    )
    if not any(
        isinstance(item, BuildingRemovedObservation)
        and item.building == added_start
        for item in removed_summary.observations
    ):
        raise RuntimeError("Removed construction action was not summarized")
    resource_deltas = [
        item.delta
        for item in removed_summary.observations
        if isinstance(item, ResourceDeltaObservation)
    ]
    if not resource_deltas or not any(delta < 0 for delta in resource_deltas):
        raise RuntimeError("Negative resource deltas were not preserved")

    left_order_plan, right_order_plan = _plans_with_different_valid_orders()
    zero_comparison = compare_build_plans(left_order_plan, right_order_plan)
    if zero_comparison.identical:
        raise RuntimeError("Different valid orders were unexpectedly identical")
    if (
        zero_comparison.action_delta != 0
        or zero_comparison.completion_date_delta != 0
        or not zero_comparison.resource_delta.is_zero()
        or zero_comparison.added_buildings
        or zero_comparison.removed_buildings
    ):
        raise RuntimeError(
            "Different-order fixture did not have zero quantified deltas"
        )
    zero_summary = summarize_plan_comparison(zero_comparison)
    if zero_summary.observations != (PlansDifferObservation(),):
        raise RuntimeError(
            "Unequal zero-delta plans were not visibly distinguished"
        )

    try:
        summarize_plan_comparison(object())
    except TypeError:
        pass
    else:
        raise RuntimeError("Non-PlanComparison input did not raise TypeError")

    if (
        forward_comparison != forward_snapshot
        or canonical != canonical_snapshot
        or wall_plan != wall_snapshot
    ):
        raise RuntimeError("Summary generation mutated an input object")

    print("Decision summary validation completed successfully.")
    print("Identical comparisons produced one identity observation and no differences.")
    print("Non-identical comparisons produced deterministic structured observations.")
    print("Right-minus-left signs were preserved.")
    print("Resource observations followed canonical ordering.")
    print("Added and removed building observations were correct.")
    print("Reversed comparisons inverted deltas and swapped building observations.")
    print("Unequal plans with zero quantified deltas remained visibly different.")
    print("Input comparisons and source plans remained unchanged.")


def _check_forward_summary(summary, wall: BuildingKey) -> None:
    observations = summary.observations
    if not isinstance(observations[0], PlansDifferObservation):
        raise RuntimeError("PlansDifferObservation was not first")

    action_index = _single_index(observations, ActionDeltaObservation)
    completion_index = _single_index(
        observations,
        CompletionDeltaObservation,
    )
    if observations[action_index].delta_actions <= 0:
        raise RuntimeError("Positive action delta was not preserved")
    if observations[completion_index].delta_days <= 0:
        raise RuntimeError("Positive completion delta was not preserved")
    if not action_index < completion_index:
        raise RuntimeError("Action observation did not precede completion")

    resource_items = [
        item
        for item in observations
        if isinstance(item, ResourceDeltaObservation)
    ]
    if not resource_items:
        raise RuntimeError("No nonzero resource observations were produced")
    resource_order = tuple(item.resource for item in resource_items)
    expected_order = tuple(
        resource
        for resource in RESOURCE_NAMES
        if getattr(summary.comparison.resource_delta, resource) != 0
    )
    if resource_order != expected_order:
        raise RuntimeError("Resource observations were not canonically ordered")

    added = [
        item.building
        for item in observations
        if isinstance(item, BuildingAddedObservation)
    ]
    if wall not in added:
        raise RuntimeError("Wall was not reported as an added building")
    if tuple(added) != tuple(sorted(added)):
        raise RuntimeError("Added buildings were not canonically ordered")


def _check_reversed_summary(forward, reverse) -> None:
    if not isinstance(reverse.observations[0], PlansDifferObservation):
        raise RuntimeError("Reversed summary changed identity category")

    forward_action = _single_value(
        forward.observations,
        ActionDeltaObservation,
        "delta_actions",
    )
    reverse_action = _single_value(
        reverse.observations,
        ActionDeltaObservation,
        "delta_actions",
    )
    if reverse_action != -forward_action:
        raise RuntimeError("Reversed action observation did not invert sign")

    forward_completion = _single_value(
        forward.observations,
        CompletionDeltaObservation,
        "delta_days",
    )
    reverse_completion = _single_value(
        reverse.observations,
        CompletionDeltaObservation,
        "delta_days",
    )
    if reverse_completion != -forward_completion:
        raise RuntimeError("Reversed completion observation did not invert sign")

    forward_resources = {
        item.resource: item.delta
        for item in forward.observations
        if isinstance(item, ResourceDeltaObservation)
    }
    reverse_resources = {
        item.resource: item.delta
        for item in reverse.observations
        if isinstance(item, ResourceDeltaObservation)
    }
    if reverse_resources != {
        resource: -delta
        for resource, delta in forward_resources.items()
    }:
        raise RuntimeError("Reversed resource observations did not invert signs")

    forward_added = tuple(
        item.building
        for item in forward.observations
        if isinstance(item, BuildingAddedObservation)
    )
    forward_removed = tuple(
        item.building
        for item in forward.observations
        if isinstance(item, BuildingRemovedObservation)
    )
    reverse_added = tuple(
        item.building
        for item in reverse.observations
        if isinstance(item, BuildingAddedObservation)
    )
    reverse_removed = tuple(
        item.building
        for item in reverse.observations
        if isinstance(item, BuildingRemovedObservation)
    )
    if reverse_added != forward_removed or reverse_removed != forward_added:
        raise RuntimeError("Reversed building observations did not swap")


def _plans_with_different_valid_orders():
    data = load_default_game_data()
    for faction in sorted(data.cities.cities):
        city = data.cities.city(faction)
        for target in sorted(city.buildings):
            graph = build_dependency_graph(city, target)
            orders = tuple(iter_topological_orders(graph, max_orders=2))
            if len(orders) >= 2:
                left = plan_build_order(city, graph, orders[0])
                right = plan_build_order(
                    city,
                    graph,
                    orders[1],
                    order_number=2,
                )
                return left, right
    raise RuntimeError("No target with multiple valid build orders was found")


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


def _single_index(observations, observation_type) -> int:
    indices = [
        index
        for index, item in enumerate(observations)
        if isinstance(item, observation_type)
    ]
    if len(indices) != 1:
        raise RuntimeError(
            f"Expected one {observation_type.__name__}, found {len(indices)}"
        )
    return indices[0]


def _single_value(observations, observation_type, attribute: str) -> int:
    matches = [
        item
        for item in observations
        if isinstance(item, observation_type)
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one {observation_type.__name__}, found {len(matches)}"
        )
    return getattr(matches[0], attribute)


if __name__ == "__main__":
    main()
