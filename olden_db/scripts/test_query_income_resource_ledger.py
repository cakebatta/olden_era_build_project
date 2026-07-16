from __future__ import annotations

import olden_db.query as query_module
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
    treasury = ResourceCost(
        gold=1_000_000,
        wood=1_000,
        ore=1_000,
        gemstones=1_000,
        crystals=1_000,
        mercury=1_000,
        dust=1_000,
        graal=1_000,
    )

    canonical = _check_canonical_and_upgrade_income(service, treasury)
    scenario = _check_scenario_consistency(service, treasury)
    _check_direct_composition_equivalence(service, treasury, scenario)
    _check_one_scenario_resolution(service, treasury, scenario)
    _check_errors(service, treasury)
    _check_determinism(service, treasury, scenario)

    if canonical.construction_total.is_zero():
        raise RuntimeError("Representative plan unexpectedly had no construction spending")
    if canonical.income_timeline is None:
        raise RuntimeError("Income-aware Query Layer returned no IncomeTimeline")

    print("Query Layer income-aware resource ledger validation completed successfully.")
    print("Canonical starting-building income was applied at beginning of day.")
    print("New income construction produced no income until the following day.")
    print("Income upgrades replaced lower levels without stacking.")
    print("One effective starting state controlled plan, income, stock, and ledger.")
    print("Recruitment after plan completion extended both timeline domains.")
    print("Query Layer output matched direct certified-domain composition.")
    print("Scenario resolution occurred exactly once per ledger request.")
    print("Existing Query Layer, scenario, action, and treasury errors propagated.")
    print("Spending totals remained unchanged while balances included income.")
    print("Repeated income-aware requests were deterministic.")


def _check_canonical_and_upgrade_income(service, treasury):
    faction = "undead"
    start = GameDate(1, 1, 1)
    dwelling = BuildingKey(faction, "Build_Tier_1", 1)
    scenario = PlanningScenario(
        (StartingBuildingOverride(dwelling, True),)
    )
    actions = (
        RecruitmentAction(
            date=GameDate(1, 1, 2),
            dwelling=dwelling,
            base_quantity=1,
        ),
    )
    ledger = service.generate_resource_ledger(
        faction,
        "Build_Main",
        2,
        actions,
        treasury,
        starting_date=start,
        scenario=scenario,
    )

    if ledger.income_timeline is None:
        raise RuntimeError("Canonical request did not include income")
    if ledger.stock.through_date != GameDate(1, 1, 2):
        raise RuntimeError("Recruitment Stock did not extend through action date")
    if ledger.income_timeline.through_date != ledger.stock.through_date:
        raise RuntimeError("Income and stock horizons differed")

    main_day_1 = [
        entry
        for entry in ledger.income_entries
        if entry.date == GameDate(1, 1, 1)
        and entry.building.sid == "Build_Main"
    ]
    if len(main_day_1) != 1 or main_day_1[0].building.level != 1:
        raise RuntimeError(
            "Canonical lower-level income was not active on the upgrade day"
        )

    main_day_2 = [
        entry
        for entry in ledger.income_entries
        if entry.date == GameDate(1, 1, 2)
        and entry.building.sid == "Build_Main"
    ]
    if len(main_day_2) != 1 or main_day_2[0].building.level != 2:
        raise RuntimeError(
            "Income upgrade did not replace the lower level on the next day"
        )

    if any(
        entry.date == GameDate(1, 1, 1)
        and entry.building.sid == "Build_Main"
        and entry.building.level == 2
        for entry in ledger.income_entries
    ):
        raise RuntimeError("Upgraded income was applied on construction day")

    spending_only = ledger.construction_total + ledger.recruitment_total
    if ledger.combined_total != spending_only:
        raise RuntimeError("Income changed factual spending totals")
    if ledger.income_total.is_zero():
        raise RuntimeError("Canonical income total was not added")

    return ledger


def _check_scenario_consistency(service, treasury):
    faction = "undead"
    main = BuildingKey(faction, "Build_Main", 1)
    dwelling = BuildingKey(faction, "Build_Tier_1", 1)
    dwelling_2 = BuildingKey(faction, "Build_Tier_1", 2)
    scenario = PlanningScenario(
        (
            StartingBuildingOverride(main, False),
            StartingBuildingOverride(dwelling, True),
            StartingBuildingOverride(dwelling_2, True),
        )
    )
    action_date = GameDate(1, 2, 1)
    actions = (
        RecruitmentAction(
            date=action_date,
            dwelling=dwelling,
            upgraded_quantity=1,
        ),
    )
    ledger = service.generate_resource_ledger(
        faction,
        "Build_Main",
        1,
        actions,
        treasury,
        scenario=scenario,
    )

    if main not in ledger.plan.order:
        raise RuntimeError("Scenario-removed income building was not constructed")
    if ledger.income_timeline is None:
        raise RuntimeError("Scenario ledger omitted IncomeTimeline")
    if ledger.stock.through_date != action_date:
        raise RuntimeError("Recruitment horizon was not honored")
    if ledger.income_timeline.through_date != action_date:
        raise RuntimeError("Income horizon did not match Recruitment Stock")
    if any(
        entry.date == ledger.plan.starting_date
        and entry.building.sid == main.sid
        for entry in ledger.income_entries
    ):
        raise RuntimeError("Scenario-removed income building produced at start")
    if len(ledger.recruitment_entries) != 1:
        raise RuntimeError("Scenario starting unlock did not reach the ledger")

    return scenario


def _check_direct_composition_equivalence(service, treasury, scenario):
    faction = "undead"
    sid = "Build_Tier_6"
    level = 1
    start = GameDate(1, 1, 1)
    dwelling = BuildingKey(faction, "Build_Tier_1", 1)
    actions = (
        RecruitmentAction(
            date=GameDate(1, 2, 1),
            dwelling=dwelling,
            upgraded_quantity=1,
        ),
    )

    query_result = service.generate_resource_ledger(
        faction,
        sid,
        level,
        actions,
        treasury,
        starting_date=start,
        scenario=scenario,
    )

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
        starting_date=start,
    )
    horizon = max(
        [plan.completion_date]
        + [action.date for action in actions],
        key=lambda date: date.day_index,
    )
    income = calculate_income_timeline(
        city,
        plan,
        through_date=horizon,
        starting_buildings=effective,
    )
    stock = calculate_recruitment_stock(
        city,
        plan,
        through_date=horizon,
        starting_buildings=effective,
    )
    direct = build_resource_ledger(
        city,
        plan,
        stock,
        actions,
        treasury,
        starting_buildings=effective,
        income_timeline=income,
    )

    if query_result != direct:
        raise RuntimeError(
            "Query Layer result differed from direct domain composition"
        )


def _check_one_scenario_resolution(service, treasury, scenario):
    original = query_module.resolve_effective_starting_buildings
    calls = 0

    def counted(city, supplied_scenario):
        nonlocal calls
        calls += 1
        return original(city, supplied_scenario)

    query_module.resolve_effective_starting_buildings = counted
    try:
        service.generate_resource_ledger(
            "undead",
            "Build_Tier_6",
            1,
            (),
            treasury,
            scenario=scenario,
        )
    finally:
        query_module.resolve_effective_starting_buildings = original

    if calls != 1:
        raise RuntimeError(
            f"Scenario resolution occurred {calls} times; expected exactly 1"
        )


def _check_errors(service, treasury):
    try:
        service.generate_resource_ledger(
            "not_a_faction",
            "Build_Main",
            1,
            (),
            treasury,
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
            treasury,
        )
    except UnknownBuildingError:
        pass
    else:
        raise RuntimeError("Unknown building did not propagate")

    invalid = PlanningScenario(
        (
            StartingBuildingOverride(
                BuildingKey("nature", "Build_Main", 1),
                True,
            ),
        )
    )
    try:
        service.generate_resource_ledger(
            "undead",
            "Build_Main",
            1,
            (),
            treasury,
            scenario=invalid,
        )
    except InvalidStartingBuildingOverrideError:
        pass
    else:
        raise RuntimeError("Invalid scenario did not propagate")

    try:
        service.generate_resource_ledger(
            "undead",
            "Build_Main",
            1,
            (object(),),
            treasury,
        )
    except TypeError:
        pass
    else:
        raise RuntimeError("Malformed recruitment action did not propagate")

    try:
        service.generate_resource_ledger(
            "undead",
            "Build_Main",
            1,
            (),
            ResourceCost(gold=-1),
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("Invalid starting resources did not propagate")


def _check_determinism(service, treasury, scenario):
    first = service.generate_resource_ledger(
        "undead",
        "Build_Tier_6",
        1,
        (),
        treasury,
        scenario=scenario,
    )
    second = service.generate_resource_ledger(
        "undead",
        "Build_Tier_6",
        1,
        (),
        treasury,
        scenario=scenario,
    )
    if first != second:
        raise RuntimeError("Repeated Query Layer requests were not deterministic")


if __name__ == "__main__":
    main()
