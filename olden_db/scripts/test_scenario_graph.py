from __future__ import annotations

from dataclasses import FrozenInstanceError

from olden_db.database import load_default_game_data
from olden_db.graph import GraphError, MissingBuildingError, build_dependency_graph
from olden_db.models import BuildingKey
from olden_db.scenario import (
    DuplicateStartingBuildingOverrideError,
    InvalidStartingBuildingOverrideError,
    PlanningScenario,
    StartingBuildingOverride,
    resolve_effective_starting_buildings,
)


def main() -> None:
    data = load_default_game_data()
    city = data.cities.city("undead")
    target = BuildingKey("undead", "Build_Tier_6", 1)
    wall = BuildingKey("undead", "Build_Wall", 1)

    before_buildings = dict(city.buildings)
    before_values = tuple(city.buildings.items())

    _check_scenario_contracts(wall)

    canonical_starting = frozenset(
        key
        for key, building in city.buildings.items()
        if building.constructed_on_start
    )
    canonical_graph = build_dependency_graph(city, target)
    explicit_canonical_graph = build_dependency_graph(
        city,
        target,
        starting_buildings=canonical_starting,
    )
    if canonical_graph != explicit_canonical_graph:
        raise RuntimeError(
            "Explicit canonical starting set changed canonical graph behavior"
        )

    empty_graph = build_dependency_graph(
        city,
        target,
        starting_buildings=frozenset(),
    )
    if empty_graph == canonical_graph:
        raise RuntimeError(
            "None and an explicitly empty starting set were treated identically"
        )
    if empty_graph.satisfied_starting_nodes:
        raise RuntimeError(
            "Explicitly empty starting set produced satisfied starting nodes"
        )

    remove_wall = PlanningScenario(
        (StartingBuildingOverride(wall, False),)
    )
    effective_without_wall = resolve_effective_starting_buildings(
        city,
        remove_wall,
    )
    if wall in effective_without_wall:
        raise RuntimeError("False override did not remove Wall from start state")

    wall_graph = build_dependency_graph(
        city,
        target,
        starting_buildings=effective_without_wall,
    )
    if wall not in wall_graph.nodes:
        raise RuntimeError("Wall did not become a required graph node")
    if wall in wall_graph.satisfied_starting_nodes:
        raise RuntimeError("Wall remained a satisfied starting node")
    if not set(city.buildings[wall].prerequisites).issubset(
        wall_graph.nodes | wall_graph.satisfied_starting_nodes
    ):
        raise RuntimeError("Wall prerequisite traversal did not continue")

    added_key = _choose_noncanonical_boundary(city, canonical_graph)
    add_scenario = PlanningScenario(
        (StartingBuildingOverride(added_key, True),)
    )
    effective_with_added = resolve_effective_starting_buildings(
        city,
        add_scenario,
    )
    added_graph = build_dependency_graph(
        city,
        target,
        starting_buildings=effective_with_added,
    )
    if added_key in added_graph.nodes:
        raise RuntimeError("Added starting building remained a required node")
    if added_key not in added_graph.satisfied_starting_nodes:
        raise RuntimeError("Added starting building was not a satisfied boundary")
    if not added_graph.nodes < canonical_graph.nodes:
        raise RuntimeError("Added starting building did not reduce graph closure")

    repeated = build_dependency_graph(
        city,
        target,
        starting_buildings=effective_with_added,
    )
    if repeated != added_graph:
        raise RuntimeError("Repeated scenario graph construction was not equal")

    _check_invalid_graph_starting_keys(city, target)
    _check_invalid_scenario_overrides(city)

    if dict(city.buildings) != before_buildings:
        raise RuntimeError("Scenario graph construction mutated city buildings")
    if tuple(city.buildings.items()) != before_values:
        raise RuntimeError("Scenario graph construction changed building objects")

    print("Scenario graph validation completed successfully.")
    print("Canonical graph behavior is preserved when starting_buildings=None.")
    print("Explicit canonical starting state produces an equivalent graph.")
    print("Explicitly empty starting state is distinct from canonical defaults.")
    print("Canonical Wall removal requires Wall construction and traversal.")
    print(f"Noncanonical starting boundary tested: {added_key.sid} L{added_key.level}")
    print("Scenario contracts are immutable, deterministic, and reject duplicates.")
    print("Canonical city and building objects remained unchanged.")


def _check_scenario_contracts(wall: BuildingKey) -> None:
    empty = PlanningScenario()
    if empty.starting_building_overrides != ():
        raise RuntimeError("Empty scenario was not accepted")

    first = StartingBuildingOverride(wall, False)
    other = StartingBuildingOverride(
        BuildingKey(wall.faction, "Build_Tier_6", 1),
        True,
    )
    scenario = PlanningScenario((other, first))
    if scenario.starting_building_overrides != tuple(sorted((other, first))):
        raise RuntimeError("Scenario overrides were not normalized deterministically")

    try:
        scenario.starting_building_overrides = ()
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise RuntimeError("PlanningScenario was mutable")

    try:
        PlanningScenario((first, StartingBuildingOverride(wall, True)))
    except DuplicateStartingBuildingOverrideError:
        pass
    else:
        raise RuntimeError("Duplicate scenario override was not rejected")


def _choose_noncanonical_boundary(city, canonical_graph) -> BuildingKey:
    candidates = sorted(
        (
            key
            for key in canonical_graph.nodes
            if city.buildings[key].prerequisites
        ),
        key=lambda key: (key.sid, key.level),
    )
    if not candidates:
        raise RuntimeError(
            "No noncanonical prerequisite with its own closure was found"
        )
    return candidates[0]


def _check_invalid_graph_starting_keys(city, target: BuildingKey) -> None:
    cross_faction = BuildingKey("human", "Build_Wall", 1)
    try:
        build_dependency_graph(
            city,
            target,
            starting_buildings=frozenset({cross_faction}),
        )
    except GraphError:
        pass
    else:
        raise RuntimeError("Cross-faction starting key was not rejected")

    unknown = BuildingKey(city.faction, "not_a_building", 1)
    try:
        build_dependency_graph(
            city,
            target,
            starting_buildings=frozenset({unknown}),
        )
    except MissingBuildingError:
        pass
    else:
        raise RuntimeError("Unknown starting key was not rejected")


def _check_invalid_scenario_overrides(city) -> None:
    cross_faction = PlanningScenario(
        (
            StartingBuildingOverride(
                BuildingKey("human", "Build_Wall", 1),
                True,
            ),
        )
    )
    try:
        resolve_effective_starting_buildings(city, cross_faction)
    except InvalidStartingBuildingOverrideError:
        pass
    else:
        raise RuntimeError("Cross-faction scenario override was not rejected")

    unknown = PlanningScenario(
        (
            StartingBuildingOverride(
                BuildingKey(city.faction, "not_a_building", 1),
                True,
            ),
        )
    )
    try:
        resolve_effective_starting_buildings(city, unknown)
    except InvalidStartingBuildingOverrideError:
        pass
    else:
        raise RuntimeError("Unknown scenario override was not rejected")


if __name__ == "__main__":
    main()
