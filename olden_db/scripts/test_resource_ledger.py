from __future__ import annotations

from olden_db.models import BuildingKey, BuildingLevel, FactionCity, ResourceCost, UnitFamily
from olden_db.planner import BuildPlan, BuildStep, GameDate
from olden_db.recruitment_stock import RecruitmentStock, calculate_recruitment_stock
from olden_db.resource_ledger import RecruitmentAction, build_resource_ledger


def main() -> None:
    _check_starting_unlock_semantics()
    _check_input_validation()
    _check_accounting_regression()
    print("Resource ledger validation completed successfully.")
    print("Canonical None starting state honored starting level-2 unlocks.")
    print("Explicit canonical starting set matched None behavior.")
    print("Explicitly empty starting state granted no initial unlocks.")
    print("Scenario-added level 2 unlocked upgraded recruitment immediately.")
    print("Scenario-removed level 2 stayed locked until construction.")
    print("Level 1 allowed base recruitment but not upgraded recruitment.")
    print("City, plan, stock, and starting-building consistency was validated.")
    print("Recruitment Stock and Resource Ledger shared one effective starting set.")
    print("Accounting, balances, deficits, stock consumption, and ordering remained unchanged.")
    print("Repeated ledger generation was deterministic.")


def _check_starting_unlock_semantics() -> None:
    faction = "unlock"
    level_1 = BuildingKey(faction, "Build_Tier_1", 1)
    level_2 = BuildingKey(faction, "Build_Tier_1", 2)
    family = _family(faction, level_1.sid)
    city = FactionCity(faction=faction, city_id="unlock")
    city.add_building(_building(level_1, family, True))
    city.add_building(_building(level_2, family, True))
    plan = _plan(faction, level_2, ())
    upgraded = (RecruitmentAction(GameDate(1, 1, 1), level_1, 0, 1),)

    canonical_stock = calculate_recruitment_stock(city, plan, through_date=GameDate(1, 1, 1))
    canonical = build_resource_ledger(
        city, plan, canonical_stock, upgraded, ResourceCost(gold=100)
    )
    if canonical.recruitment_total != ResourceCost(gold=20):
        raise RuntimeError("canonical level-2 unlock failed")

    canonical_set = frozenset({level_1, level_2})
    explicit_stock = calculate_recruitment_stock(
        city, plan, through_date=GameDate(1, 1, 1), starting_buildings=canonical_set
    )
    explicit = build_resource_ledger(
        city,
        plan,
        explicit_stock,
        upgraded,
        ResourceCost(gold=100),
        starting_buildings=canonical_set,
    )
    if explicit != canonical:
        raise RuntimeError("explicit canonical set did not match None")

    added_city = FactionCity(faction=faction, city_id="added")
    added_city.add_building(_building(level_1, family))
    added_city.add_building(_building(level_2, family))
    added_set = frozenset({level_1, level_2})
    added_stock = calculate_recruitment_stock(
        added_city, plan, through_date=GameDate(1, 1, 1), starting_buildings=added_set
    )
    added = build_resource_ledger(
        added_city,
        plan,
        added_stock,
        upgraded,
        ResourceCost(gold=100),
        starting_buildings=added_set,
    )
    if added.recruitment_entries[0].stock_after != 4:
        raise RuntimeError("scenario-added level 2 did not consume shared stock")

    empty_stock = calculate_recruitment_stock(
        city, plan, through_date=GameDate(1, 1, 1), starting_buildings=frozenset()
    )
    _expect_value_error(
        lambda: build_resource_ledger(
            city,
            plan,
            empty_stock,
            upgraded,
            ResourceCost(gold=100),
            starting_buildings=frozenset(),
        ),
        "empty starting state unlocked upgrades",
    )

    level_1_only = frozenset({level_1})
    level_1_stock = calculate_recruitment_stock(
        city, plan, through_date=GameDate(1, 1, 1), starting_buildings=level_1_only
    )
    base = build_resource_ledger(
        city,
        plan,
        level_1_stock,
        (RecruitmentAction(GameDate(1, 1, 1), level_1, 1, 0),),
        ResourceCost(gold=100),
        starting_buildings=level_1_only,
    )
    if base.recruitment_total != ResourceCost(gold=10):
        raise RuntimeError("level 1 blocked base recruitment")
    _expect_value_error(
        lambda: build_resource_ledger(
            city,
            plan,
            level_1_stock,
            upgraded,
            ResourceCost(gold=100),
            starting_buildings=level_1_only,
        ),
        "level 1 unlocked upgrades",
    )

    removal_plan = _plan(
        faction,
        level_2,
        (_step(1, GameDate(1, 1, 2), level_2, ResourceCost()),),
    )
    removal_stock = calculate_recruitment_stock(
        city,
        removal_plan,
        through_date=GameDate(1, 1, 2),
        starting_buildings=level_1_only,
    )
    _expect_value_error(
        lambda: build_resource_ledger(
            city,
            removal_plan,
            removal_stock,
            upgraded,
            ResourceCost(gold=100),
            starting_buildings=level_1_only,
        ),
        "removed level 2 unlocked before construction",
    )
    after = build_resource_ledger(
        city,
        removal_plan,
        removal_stock,
        (RecruitmentAction(GameDate(1, 1, 2), level_1, 0, 1),),
        ResourceCost(gold=100),
        starting_buildings=level_1_only,
    )
    if after.recruitment_total != ResourceCost(gold=20):
        raise RuntimeError("same-day level-2 construction did not unlock upgrades")


def _check_input_validation() -> None:
    faction = "check"
    level_1 = BuildingKey(faction, "Build_Tier_1", 1)
    level_2 = BuildingKey(faction, "Build_Tier_1", 2)
    family = _family(faction, level_1.sid)
    city = FactionCity(faction=faction, city_id="check")
    city.add_building(_building(level_1, family, True))
    city.add_building(_building(level_2, family, True))
    plan = _plan(faction, level_2, ())
    stock = calculate_recruitment_stock(city, plan, through_date=GameDate(1, 1, 1))

    wrong_city = FactionCity(faction="other", city_id="wrong")
    _expect_value_error(
        lambda: build_resource_ledger(wrong_city, plan, stock, (), ResourceCost()),
        "faction mismatch accepted",
    )
    bad_stock = RecruitmentStock(
        faction=stock.faction,
        starting_date=GameDate(1, 1, 2),
        through_date=GameDate(1, 1, 2),
        entries=stock.entries,
    )
    _expect_value_error(
        lambda: build_resource_ledger(city, plan, bad_stock, (), ResourceCost()),
        "starting-date mismatch accepted",
    )
    _expect_value_error(
        lambda: build_resource_ledger(
            city,
            plan,
            stock,
            (),
            ResourceCost(),
            starting_buildings=frozenset({BuildingKey(faction, "Build_Unknown", 1)}),
        ),
        "unknown starting building accepted",
    )
    _expect_value_error(
        lambda: build_resource_ledger(
            city,
            plan,
            stock,
            (),
            ResourceCost(),
            starting_buildings=frozenset({BuildingKey("other", "Build_Tier_1", 1)}),
        ),
        "cross-faction starting building accepted",
    )
    try:
        build_resource_ledger(city, plan, stock, (), ResourceCost(), starting_buildings=set())
    except TypeError:
        pass
    else:
        raise RuntimeError("malformed starting collection accepted")


def _check_accounting_regression() -> None:
    faction = "acct"
    level_1 = BuildingKey(faction, "Build_Tier_1", 1)
    level_2 = BuildingKey(faction, "Build_Tier_1", 2)
    family = _family(faction, level_1.sid)
    city = FactionCity(faction=faction, city_id="acct")
    city.add_building(_building(level_1, family))
    city.add_building(_building(level_2, family))
    plan = _plan(
        faction,
        level_2,
        (
            _step(1, GameDate(1, 1, 1), level_1, ResourceCost(gold=10)),
            _step(2, GameDate(1, 1, 2), level_2, ResourceCost(gold=20)),
        ),
    )
    effective = frozenset()
    stock = calculate_recruitment_stock(
        city, plan, through_date=GameDate(1, 2, 1), starting_buildings=effective
    )
    actions = (
        RecruitmentAction(GameDate(1, 1, 1), level_1, 1, 0),
        RecruitmentAction(GameDate(1, 1, 2), level_1, 1, 1),
    )
    first = build_resource_ledger(
        city,
        plan,
        stock,
        actions,
        ResourceCost(gold=100),
        starting_buildings=effective,
    )
    second = build_resource_ledger(
        city,
        plan,
        stock,
        actions,
        ResourceCost(gold=100),
        starting_buildings=effective,
    )
    if first != second:
        raise RuntimeError("ledger was not deterministic")
    if first.combined_total != first.construction_total + first.recruitment_total:
        raise RuntimeError("totals changed")
    if not first.feasible or first.first_deficit is not None:
        raise RuntimeError("feasibility changed")


def _family(faction: str, sid: str) -> UnitFamily:
    return UnitFamily(
        faction=faction,
        tier=1,
        dwelling_sid=sid,
        base_sid="Base",
        upgrade_option_1_sid="Upgrade_A",
        upgrade_option_2_sid="Upgrade_B",
        weekly_growth=5,
        base_cost=ResourceCost(gold=10),
        upgraded_cost=ResourceCost(gold=20),
    )


def _building(key, family=None, constructed_on_start=False) -> BuildingLevel:
    return BuildingLevel(
        key=key,
        category="test",
        name_key=None,
        scene_slot=None,
        cost=ResourceCost(),
        constructed_on_start=constructed_on_start,
        unit_family=family,
    )


def _plan(faction, target, steps) -> BuildPlan:
    return BuildPlan(
        faction=faction,
        target=target,
        order_number=1,
        steps=steps,
        total_cost=ResourceCost(),
        starting_date=GameDate(1, 1, 1),
    )


def _step(number, date, building, cost) -> BuildStep:
    return BuildStep(
        step_number=number,
        date=date,
        building=building,
        individual_cost=cost,
        cumulative_cost=ResourceCost(),
    )


def _expect_value_error(callback, message: str) -> None:
    try:
        callback()
    except ValueError:
        return
    raise RuntimeError(message)


if __name__ == "__main__":
    main()
