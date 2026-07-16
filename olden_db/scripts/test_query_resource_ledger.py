from __future__ import annotations

from olden_db.database import load_default_game_data
from olden_db.graph import build_dependency_graph, iter_topological_orders
from olden_db.income_timeline import calculate_income_timeline
from olden_db.models import BuildingKey, ResourceCost
from olden_db.planner import GameDate, plan_build_order
from olden_db.query import (
    PlanningQueryService,
    UnknownBuildingError,
    UnknownFactionError,
)
from olden_db.recruitment_stock import calculate_recruitment_stock
from olden_db.resource_ledger import RecruitmentAction, build_resource_ledger
from olden_db.scenario import (
    InvalidStartingBuildingOverrideError,
    PlanningScenario,
    StartingBuildingOverride,
    resolve_effective_starting_buildings,
)


def main() -> None:
    service = PlanningQueryService.from_default_game_data()
    faction = "undead"
    target_sid = "Build_Tier_6"
    target_level = 1
    starting_date = GameDate(1, 1, 1)
    starting_resources = ResourceCost(
        gold=1_000_000,
        wood=1_000,
        ore=1_000,
        gemstones=1_000,
        crystals=1_000,
        mercury=1_000,
        dust=1_000,
        graal=1_000,
    )

    canonical = service.generate_resource_ledger(
        faction,
        target_sid,
        target_level,
        (),
        starting_resources,
        starting_date=starting_date,
    )
    if canonical.plan.faction != faction:
        raise RuntimeError("Canonical ledger returned the wrong faction")
    if canonical.plan.starting_date != starting_date:
        raise RuntimeError("Canonical ledger returned the wrong starting date")
    if canonical.stock.starting_date != starting_date:
        raise RuntimeError("Canonical stock and plan starting dates differed")
    if canonical.income_timeline is None:
        raise RuntimeError("Query Layer did not generate an IncomeTimeline")
    if canonical.income_timeline.starting_date != starting_date:
        raise RuntimeError("Income timeline and plan starting dates differed")
    if canonical.income_total != canonical.income_timeline.total_income:
        raise RuntimeError("Ledger income total differed from its timeline")

    scenario = PlanningScenario(
        (
            StartingBuildingOverride(
                BuildingKey(faction, "Build_Wall", 1),
                False,
            ),
        )
    )
    scenario_ledger = service.generate_resource_ledger(
        faction,
        target_sid,
        target_level,
        (),
        starting_resources,
        starting_date=starting_date,
        scenario=scenario,
    )

    direct = _direct_composition(
        faction,
        target_sid,
        target_level,
        starting_date,
        scenario,
        (),
        starting_resources,
    )
    if scenario_ledger != direct:
        raise RuntimeError(
            "Query Layer ledger differed from direct backend composition"
        )

    repeated = service.generate_resource_ledger(
        faction,
        target_sid,
        target_level,
        (),
        starting_resources,
        starting_date=starting_date,
        scenario=scenario,
    )
    if repeated != scenario_ledger:
        raise RuntimeError("Repeated Query Layer ledgers were not deterministic")

    _check_recruitment_action_pipeline(service, starting_resources)
    _check_errors(service, starting_resources)

    print("Query Layer resource ledger validation completed successfully.")
    print("Canonical ledger generation succeeded.")
    print("Scenario ledger generation reused one effective starting state.")
    print("Query Layer output matched direct backend composition.")
    print("Plan, income, stock, and ledger shared faction and starting-date context.")
    print("Deterministic town income was included automatically.")
    print("Recruitment actions were coordinated through stock and ledger generation.")
    print("Repeated results were deterministic.")
    print("Existing Query Layer and scenario errors propagated unchanged.")


def _direct_composition(
    faction,
    sid,
    level,
    starting_date,
    scenario,
    actions,
    starting_resources,
):
    data = load_default_game_data()
    city = data.cities.city(faction)
    effective = resolve_effective_starting_buildings(city, scenario)
    target = city.get(sid, level)
    graph = build_dependency_graph(
        city,
        target.key,
        starting_buildings=effective,
    )
    order = next(iter_topological_orders(graph))
    plan = plan_build_order(
        city,
        graph,
        order,
        starting_date=starting_date,
    )
    through_date = plan.completion_date
    for action in actions:
        if action.date.day_index > through_date.day_index:
            through_date = action.date
    income_timeline = calculate_income_timeline(
        city,
        plan,
        through_date=through_date,
        starting_buildings=effective,
    )
    stock = calculate_recruitment_stock(
        city,
        plan,
        through_date=through_date,
        starting_buildings=effective,
    )
    return build_resource_ledger(
        city,
        plan,
        stock,
        actions,
        starting_resources,
        starting_buildings=effective,
        income_timeline=income_timeline,
    )


def _check_recruitment_action_pipeline(service, starting_resources) -> None:
    faction = "undead"
    dwelling = BuildingKey(faction, "Build_Tier_1", 1)
    level_2 = BuildingKey(faction, "Build_Tier_1", 2)
    scenario = PlanningScenario(
        (
            StartingBuildingOverride(dwelling, True),
            StartingBuildingOverride(level_2, True),
        )
    )
    actions = (
        RecruitmentAction(
            date=GameDate(1, 1, 1),
            dwelling=dwelling,
            upgraded_quantity=1,
        ),
    )
    ledger = service.generate_resource_ledger(
        faction,
        "Build_Tier_1",
        2,
        actions,
        starting_resources,
        scenario=scenario,
    )
    if len(ledger.recruitment_entries) != 1:
        raise RuntimeError("Recruitment action was not included in the ledger")
    if ledger.recruitment_entries[0].stock_after < 0:
        raise RuntimeError("Recruitment action produced negative creature stock")


def _check_errors(service, starting_resources) -> None:
    try:
        service.generate_resource_ledger(
            "not_a_faction",
            "Build_Tier_1",
            1,
            (),
            starting_resources,
        )
    except UnknownFactionError:
        pass
    else:
        raise RuntimeError("Unknown faction did not propagate")

    try:
        service.generate_resource_ledger(
            "undead",
            "not_a_building",
            1,
            (),
            starting_resources,
        )
    except UnknownBuildingError:
        pass
    else:
        raise RuntimeError("Unknown building did not propagate")

    invalid = PlanningScenario(
        (
            StartingBuildingOverride(
                BuildingKey("nature", "Build_Wall", 1),
                True,
            ),
        )
    )
    try:
        service.generate_resource_ledger(
            "undead",
            "Build_Tier_1",
            1,
            (),
            starting_resources,
            scenario=invalid,
        )
    except InvalidStartingBuildingOverrideError:
        pass
    else:
        raise RuntimeError("Invalid scenario did not propagate")


if __name__ == "__main__":
    main()
