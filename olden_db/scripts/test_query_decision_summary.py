from __future__ import annotations

from olden_db.decision_summary import (
    BuildingAddedObservation,
    PlansDifferObservation,
    PlansIdenticalObservation,
    summarize_plan_comparison,
)
from olden_db.models import BuildingKey
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

    identical = service.generate_decision_summary(
        target.faction,
        target.sid,
        target.level,
        right_faction=target.faction,
        right_sid=target.sid,
        right_level=target.level,
    )
    if identical.observations != (PlansIdenticalObservation(),):
        raise RuntimeError("Identical plans did not produce identical summary")

    remove_wall = PlanningScenario(
        (StartingBuildingOverride(wall, False),)
    )
    canonical_to_scenario = service.generate_decision_summary(
        target.faction,
        target.sid,
        target.level,
        right_faction=target.faction,
        right_sid=target.sid,
        right_level=target.level,
        right_scenario=remove_wall,
    )
    if not isinstance(
        canonical_to_scenario.observations[0],
        PlansDifferObservation,
    ):
        raise RuntimeError("Canonical-to-scenario summary was not different")
    if not any(
        isinstance(item, BuildingAddedObservation)
        and item.building == wall
        for item in canonical_to_scenario.observations
    ):
        raise RuntimeError("Wall addition was not summarized")

    direct = summarize_plan_comparison(
        service.compare_plans(
            target.faction,
            target.sid,
            target.level,
            right_faction=target.faction,
            right_sid=target.sid,
            right_level=target.level,
            right_scenario=remove_wall,
        )
    )
    if canonical_to_scenario != direct:
        raise RuntimeError(
            "Query Layer summary differed from direct summary composition"
        )

    scenario_a = PlanningScenario(
        (StartingBuildingOverride(wall, False),)
    )
    scenario_b = PlanningScenario()
    two_scenarios = service.generate_decision_summary(
        target.faction,
        target.sid,
        target.level,
        left_scenario=scenario_a,
        right_faction=target.faction,
        right_sid=target.sid,
        right_level=target.level,
        right_scenario=scenario_b,
    )
    if not isinstance(two_scenarios.observations[0], PlansDifferObservation):
        raise RuntimeError("Independent scenarios did not produce a difference")

    repeated = service.generate_decision_summary(
        target.faction,
        target.sid,
        target.level,
        right_faction=target.faction,
        right_sid=target.sid,
        right_level=target.level,
        right_scenario=remove_wall,
    )
    if repeated != canonical_to_scenario:
        raise RuntimeError("Repeated Query Layer summaries were not deterministic")

    _check_query_errors(service, target)
    _check_scenario_error(service, target)

    print("Query Layer decision summary validation completed successfully.")
    print("Identical plans produced PlansIdenticalObservation.")
    print("Canonical and scenario plans produced expected observations.")
    print("Independent left and right scenarios were supported.")
    print("Query Layer and scenario errors propagated unchanged.")
    print("Repeated summaries were deterministic.")
    print("Query Layer summaries matched direct summary composition.")


def _check_query_errors(
    service: PlanningQueryService,
    target: BuildingKey,
) -> None:
    try:
        service.generate_decision_summary(
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
        raise RuntimeError("Unknown faction did not propagate")

    try:
        service.generate_decision_summary(
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
        raise RuntimeError("Unknown building did not propagate")


def _check_scenario_error(
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
        service.generate_decision_summary(
            target.faction,
            target.sid,
            target.level,
            left_scenario=invalid,
            right_faction=target.faction,
            right_sid=target.sid,
            right_level=target.level,
        )
    except InvalidStartingBuildingOverrideError:
        pass
    else:
        raise RuntimeError("Invalid scenario did not propagate")


if __name__ == "__main__":
    main()
