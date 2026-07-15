from __future__ import annotations

from dataclasses import FrozenInstanceError

from olden_db.models import (
    BuildingKey,
    BuildingLevel,
    FactionCity,
    ResourceCost,
    UnitFamily,
)
from olden_db.planner import BuildPlan, BuildStep, GameDate
from olden_db.recruitment_stock import calculate_recruitment_stock


def main() -> None:
    city, plan, keys = _fixture()
    city_snapshot = dict(city.buildings)
    plan_snapshot = plan
    through = GameDate(1, 4, 1)

    canonical = calculate_recruitment_stock(
        city,
        plan,
        through_date=through,
    )
    canonical_starting = frozenset(
        key
        for key, building in city.buildings.items()
        if building.constructed_on_start
    )
    explicit_canonical = calculate_recruitment_stock(
        city,
        plan,
        through_date=through,
        starting_buildings=canonical_starting,
    )
    if canonical != explicit_canonical:
        raise RuntimeError(
            "Explicit canonical starting set did not match default behavior"
        )

    empty = calculate_recruitment_stock(
        city,
        plan,
        through_date=through,
        starting_buildings=frozenset(),
    )
    if empty == canonical:
        raise RuntimeError("Explicitly empty starting state matched canonical state")
    _expect(canonical, keys["dwelling_c"], GameDate(1, 1, 1), 2)
    _expect(empty, keys["dwelling_c"], GameDate(1, 1, 1), 0)

    added_dwelling = calculate_recruitment_stock(
        city,
        plan,
        through_date=through,
        starting_buildings=frozenset(
            canonical_starting | {keys["dwelling_b"]}
        ),
    )
    _expect(added_dwelling, keys["dwelling_b"], GameDate(1, 1, 1), 3)
    _expect(added_dwelling, keys["dwelling_b"], GameDate(1, 2, 1), 6)

    _check_removed_starting_wall()
    _check_invalid_starting_keys(city, plan)

    repeated = calculate_recruitment_stock(
        city,
        plan,
        through_date=through,
        starting_buildings=frozenset(),
    )
    if repeated != empty:
        raise RuntimeError("Explicit starting-state calculation was not deterministic")

    _check_original_growth_rules(canonical, keys)

    try:
        canonical.entries[0].available = 999
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise RuntimeError("Dwelling stock entry was mutable")

    if city.buildings != city_snapshot or plan != plan_snapshot:
        raise RuntimeError("Stock calculation mutated canonical inputs")

    print("Recruitment stock validation completed successfully.")
    print("Default calculation preserved canonical starting-state behavior.")
    print("Explicit canonical starting set matched the default calculation.")
    print("Explicitly empty starting state remained distinct from None.")
    print("Scenario-added dwellings received initial stock and later growth.")
    print("Removed starting walls affected only later post-construction weeks.")
    print("Unknown and cross-faction starting keys were rejected.")
    print("Existing timing, rounding, accumulation, and multi-dwelling rules passed.")
    print("Repeated calculations were deterministic.")
    print("Results and source inputs remained immutable.")


def _check_original_growth_rules(stock, keys) -> None:
    _expect(stock, keys["dwelling_a"], GameDate(1, 1, 1), 5)
    _expect(stock, keys["dwelling_b"], GameDate(1, 1, 1), 0)
    _expect(stock, keys["dwelling_c"], GameDate(1, 1, 1), 2)
    _expect(stock, keys["dwelling_a"], GameDate(1, 2, 1), 10)
    _expect(stock, keys["dwelling_b"], GameDate(1, 2, 2), 3)
    _expect(stock, keys["dwelling_a"], GameDate(1, 3, 1), 17)
    _expect(stock, keys["dwelling_b"], GameDate(1, 3, 1), 7)
    _expect(stock, keys["dwelling_c"], GameDate(1, 3, 1), 7)
    _expect(stock, keys["dwelling_a"], GameDate(1, 4, 1), 27)
    _expect(stock, keys["dwelling_b"], GameDate(1, 4, 1), 13)
    _expect(stock, keys["dwelling_c"], GameDate(1, 4, 1), 11)


def _check_removed_starting_wall() -> None:
    faction = "undead"
    dwelling = BuildingKey(faction, "Build_Tier_1", 1)
    wall = BuildingKey(faction, "Build_Wall", 2)
    family = _family(faction, 1, dwelling.sid, 5)

    city = FactionCity(faction=faction, city_id="undead_test")
    city.add_building(
        _building(
            dwelling,
            family,
            constructed_on_start=True,
        )
    )
    city.add_building(
        _building(
            wall,
            constructed_on_start=True,
        )
    )
    city_snapshot = dict(city.buildings)

    plan = BuildPlan(
        faction=faction,
        target=wall,
        order_number=1,
        steps=(
            _step(1, GameDate(1, 2, 2), wall),
        ),
        total_cost=ResourceCost(),
        starting_date=GameDate(1, 1, 1),
    )

    effective = frozenset({dwelling})
    stock = calculate_recruitment_stock(
        city,
        plan,
        through_date=GameDate(1, 3, 1),
        starting_buildings=effective,
    )
    _expect(stock, dwelling, GameDate(1, 1, 1), 5)
    _expect(stock, dwelling, GameDate(1, 2, 1), 10)
    _expect(stock, dwelling, GameDate(1, 3, 1), 17)

    if city.buildings != city_snapshot:
        raise RuntimeError("Removed-wall calculation mutated canonical city")


def _check_invalid_starting_keys(city, plan) -> None:
    unknown = BuildingKey(city.faction, "Build_Unknown", 1)
    try:
        calculate_recruitment_stock(
            city,
            plan,
            starting_buildings=frozenset({unknown}),
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("Unknown starting building was not rejected")

    cross_faction = BuildingKey("other", "Build_Tier_1", 1)
    try:
        calculate_recruitment_stock(
            city,
            plan,
            starting_buildings=frozenset({cross_faction}),
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("Cross-faction starting building was not rejected")


def _expect(stock, dwelling: BuildingKey, date: GameDate, expected: int) -> None:
    actual = stock.available(dwelling, date)
    if actual != expected:
        raise RuntimeError(
            f"Unexpected stock for {dwelling} on {date}: "
            f"expected {expected}, got {actual}"
        )


def _fixture():
    faction = "test"
    dwelling_a = BuildingKey(faction, "Build_Tier_1", 1)
    dwelling_b = BuildingKey(faction, "Build_Tier_2", 1)
    dwelling_c = BuildingKey(faction, "Build_Tier_3", 1)
    wall_2 = BuildingKey(faction, "Build_Wall", 2)
    wall_3 = BuildingKey(faction, "Build_Wall", 3)

    family_a = _family(faction, 1, dwelling_a.sid, 5)
    family_b = _family(faction, 2, dwelling_b.sid, 3)
    family_c = _family(faction, 3, dwelling_c.sid, 2)

    city = FactionCity(faction=faction, city_id="test_city")
    city.add_building(_building(dwelling_a, family_a))
    city.add_building(_building(dwelling_b, family_b))
    city.add_building(
        _building(
            dwelling_c,
            family_c,
            constructed_on_start=True,
        )
    )
    city.add_building(_building(wall_2))
    city.add_building(_building(wall_3))

    steps = (
        _step(1, GameDate(1, 1, 1), dwelling_a),
        _step(2, GameDate(1, 2, 1), wall_2),
        _step(3, GameDate(1, 2, 2), dwelling_b),
        _step(4, GameDate(1, 3, 2), wall_3),
    )
    plan = BuildPlan(
        faction=faction,
        target=wall_3,
        order_number=1,
        steps=steps,
        total_cost=ResourceCost(),
        starting_date=GameDate(1, 1, 1),
    )
    return city, plan, {
        "dwelling_a": dwelling_a,
        "dwelling_b": dwelling_b,
        "dwelling_c": dwelling_c,
    }


def _family(
    faction: str,
    tier: int,
    dwelling_sid: str,
    growth: int,
) -> UnitFamily:
    return UnitFamily(
        faction=faction,
        tier=tier,
        dwelling_sid=dwelling_sid,
        base_sid=f"Unit_{tier}_Base",
        upgrade_option_1_sid=f"Unit_{tier}_Upgrade_A",
        upgrade_option_2_sid=f"Unit_{tier}_Upgrade_B",
        weekly_growth=growth,
        base_cost=ResourceCost(gold=1),
        upgraded_cost=ResourceCost(gold=2),
    )


def _building(
    key: BuildingKey,
    family: UnitFamily | None = None,
    *,
    constructed_on_start: bool = False,
) -> BuildingLevel:
    return BuildingLevel(
        key=key,
        category="test",
        name_key=None,
        scene_slot=None,
        cost=ResourceCost(),
        constructed_on_start=constructed_on_start,
        unit_family=family,
    )


def _step(number: int, date: GameDate, building: BuildingKey) -> BuildStep:
    return BuildStep(
        step_number=number,
        date=date,
        building=building,
        individual_cost=ResourceCost(),
        cumulative_cost=ResourceCost(),
    )


if __name__ == "__main__":
    main()
