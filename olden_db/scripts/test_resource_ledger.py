from __future__ import annotations

from dataclasses import FrozenInstanceError

from olden_db.models import BuildingKey, BuildingLevel, FactionCity, ResourceCost, UnitFamily
from olden_db.planner import BuildPlan, BuildStep, GameDate
from olden_db.recruitment_stock import calculate_recruitment_stock
from olden_db.resource_ledger import RecruitmentAction, build_resource_ledger


def main() -> None:
    city, plan, keys = _fixture()
    stock = calculate_recruitment_stock(city, plan, through_date=GameDate(1, 3, 1))
    plan_snapshot = plan
    stock_snapshot = stock

    construction_only = build_resource_ledger(
        plan, stock, (), ResourceCost(gold=1000, wood=100)
    )
    if not construction_only.feasible:
        raise RuntimeError("Construction-only ledger was unexpectedly infeasible")
    if construction_only.recruitment_total != ResourceCost():
        raise RuntimeError("Construction-only ledger had recruitment spending")
    if construction_only.combined_total != construction_only.construction_total:
        raise RuntimeError("Construction-only combined total was incorrect")

    actions = (
        RecruitmentAction(GameDate(1, 1, 1), keys["dwelling_a"], 2, 0),
        RecruitmentAction(GameDate(1, 2, 1), keys["dwelling_a"], 1, 2),
        RecruitmentAction(GameDate(1, 2, 2), keys["dwelling_b"], 1, 1),
        RecruitmentAction(GameDate(1, 3, 1), keys["dwelling_a"], 3, 0),
    )
    ledger = build_resource_ledger(
        plan, stock, actions, ResourceCost(gold=1000, wood=100)
    )
    if not ledger.feasible or ledger.first_deficit is not None:
        raise RuntimeError("Sufficient-resource ledger was infeasible")
    if len(ledger.construction_entries) != len(plan.steps):
        raise RuntimeError("Construction entries were incomplete")
    if len(ledger.recruitment_entries) != len(actions):
        raise RuntimeError("Recruitment entries were incomplete")
    if ledger.combined_total != ledger.construction_total + ledger.recruitment_total:
        raise RuntimeError("Separate and combined totals disagreed")
    if ledger.recruitment_entries[1].cost != ResourceCost(gold=50):
        raise RuntimeError("Mixed base/upgraded recruitment cost was incorrect")
    if ledger.recruitment_entries[0].stock_before != 5:
        raise RuntimeError("Initial stock was not consumed correctly")
    if ledger.recruitment_entries[1].stock_before != 8:
        raise RuntimeError("Earlier purchases did not reduce later stock")

    insufficient = build_resource_ledger(plan, stock, actions, ResourceCost(gold=35))
    if insufficient.feasible or insufficient.first_deficit is None:
        raise RuntimeError("Insufficient resources did not produce a deficit")
    if insufficient.first_deficit.date != GameDate(1, 1, 2):
        raise RuntimeError("First deficit date was incorrect")
    if insufficient.first_deficit.resource != "gold":
        raise RuntimeError("First deficit resource was incorrect")

    _check_duplicate_rejection(plan, stock, keys)
    _check_shared_stock(plan, stock, keys)
    _check_unlock(plan, stock, keys)
    _check_same_day_construction_and_recruitment(city)
    _check_determinism(plan, stock, actions)

    try:
        ledger.actions = ()
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise RuntimeError("Resource ledger was mutable")

    if plan != plan_snapshot or stock != stock_snapshot:
        raise RuntimeError("Ledger generation mutated source inputs")

    print("Resource ledger validation completed successfully.")
    print("Construction-only and recruitment ledgers were generated.")
    print("Sufficient and insufficient resource outcomes were distinguished.")
    print("First deficit date and canonical resource were reported.")
    print("Base, upgraded, and mixed recruitment costs were calculated.")
    print("Shared dwelling stock and repeated-purchase consumption were enforced.")
    print("Dwelling level-2 unlock rules were enforced.")
    print("Same-day construction and recruitment were supported.")
    print("Weekly accumulation was consumed from RecruitmentStock.")
    print("Duplicate dwelling/date actions were rejected.")
    print("Entry ordering, totals, determinism, and immutability were preserved.")


def _check_duplicate_rejection(plan, stock, keys) -> None:
    duplicate = (
        RecruitmentAction(GameDate(1, 1, 1), keys["dwelling_a"], 1, 0),
        RecruitmentAction(GameDate(1, 1, 1), keys["dwelling_a"], 1, 0),
    )
    try:
        build_resource_ledger(plan, stock, duplicate, ResourceCost(gold=1000))
    except ValueError:
        pass
    else:
        raise RuntimeError("Duplicate dwelling/date actions were not rejected")


def _check_shared_stock(plan, stock, keys) -> None:
    too_many = (RecruitmentAction(GameDate(1, 1, 1), keys["dwelling_a"], 3, 3),)
    try:
        build_resource_ledger(plan, stock, too_many, ResourceCost(gold=1000))
    except ValueError:
        pass
    else:
        raise RuntimeError("Shared stock over-consumption was not rejected")


def _check_unlock(plan, stock, keys) -> None:
    locked = (RecruitmentAction(GameDate(1, 1, 1), keys["dwelling_a"], 0, 1),)
    try:
        build_resource_ledger(plan, stock, locked, ResourceCost(gold=1000))
    except ValueError:
        pass
    else:
        raise RuntimeError("Upgraded recruitment before level 2 was not rejected")


def _check_same_day_construction_and_recruitment(city) -> None:
    faction = city.faction
    dwelling = BuildingKey(faction, "Build_Tier_4", 1)
    level_2 = BuildingKey(faction, "Build_Tier_4", 2)
    family = _family(faction, 4, dwelling.sid, 4)
    local = FactionCity(faction=faction, city_id="same_day")
    local.add_building(_building(dwelling, family))
    local.add_building(_building(level_2, family))
    plan = BuildPlan(
        faction=faction,
        target=level_2,
        order_number=1,
        steps=(
            _step(1, GameDate(1, 1, 1), dwelling, ResourceCost(gold=10)),
            _step(2, GameDate(1, 1, 2), level_2, ResourceCost(gold=10)),
        ),
        total_cost=ResourceCost(gold=20),
        starting_date=GameDate(1, 1, 1),
    )
    stock = calculate_recruitment_stock(
        local,
        plan,
        through_date=GameDate(1, 1, 2),
        starting_buildings=frozenset(),
    )
    ledger = build_resource_ledger(
        plan,
        stock,
        (RecruitmentAction(GameDate(1, 1, 2), dwelling, 0, 1),),
        ResourceCost(gold=100),
    )
    if not ledger.feasible or ledger.recruitment_entries[0].stock_before != 4:
        raise RuntimeError("Same-day level-2 construction/recruitment failed")


def _check_determinism(plan, stock, actions) -> None:
    first = build_resource_ledger(plan, stock, actions, ResourceCost(gold=1000, wood=100))
    second = build_resource_ledger(plan, stock, actions, ResourceCost(gold=1000, wood=100))
    if first != second:
        raise RuntimeError("Repeated ledger generation was not deterministic")


def _fixture():
    faction = "test"
    dwelling_a = BuildingKey(faction, "Build_Tier_1", 1)
    dwelling_a_2 = BuildingKey(faction, "Build_Tier_1", 2)
    dwelling_b = BuildingKey(faction, "Build_Tier_2", 1)
    dwelling_b_2 = BuildingKey(faction, "Build_Tier_2", 2)
    family_a = _family(faction, 1, dwelling_a.sid, 5)
    family_b = _family(faction, 2, dwelling_b.sid, 3)
    city = FactionCity(faction=faction, city_id="ledger_test")
    city.add_building(_building(dwelling_a, family_a))
    city.add_building(_building(dwelling_a_2, family_a))
    city.add_building(_building(dwelling_b, family_b))
    city.add_building(_building(dwelling_b_2, family_b))
    steps = (
        _step(1, GameDate(1, 1, 1), dwelling_a, ResourceCost(gold=10)),
        _step(2, GameDate(1, 1, 2), dwelling_a_2, ResourceCost(gold=20)),
        _step(3, GameDate(1, 2, 1), dwelling_b, ResourceCost(gold=30)),
        _step(4, GameDate(1, 2, 2), dwelling_b_2, ResourceCost(gold=40)),
    )
    plan = BuildPlan(
        faction=faction,
        target=dwelling_b_2,
        order_number=1,
        steps=steps,
        total_cost=ResourceCost(gold=100),
        starting_date=GameDate(1, 1, 1),
    )
    return city, plan, {"dwelling_a": dwelling_a, "dwelling_b": dwelling_b}


def _family(faction: str, tier: int, sid: str, growth: int) -> UnitFamily:
    return UnitFamily(
        faction=faction,
        tier=tier,
        dwelling_sid=sid,
        base_sid=f"Base_{tier}",
        upgrade_option_1_sid=f"Upgrade_A_{tier}",
        upgrade_option_2_sid=f"Upgrade_B_{tier}",
        weekly_growth=growth,
        base_cost=ResourceCost(gold=10),
        upgraded_cost=ResourceCost(gold=20),
    )


def _building(key, family=None) -> BuildingLevel:
    return BuildingLevel(
        key=key,
        category="test",
        name_key=None,
        scene_slot=None,
        cost=ResourceCost(),
        unit_family=family,
    )


def _step(number, date, building, cost) -> BuildStep:
    return BuildStep(
        step_number=number,
        date=date,
        building=building,
        individual_cost=cost,
        cumulative_cost=ResourceCost(),
    )


if __name__ == "__main__":
    main()
