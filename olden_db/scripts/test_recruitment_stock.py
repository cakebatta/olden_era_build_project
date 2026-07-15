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

    first = calculate_recruitment_stock(
        city,
        plan,
        through_date=GameDate(1, 4, 1),
    )
    second = calculate_recruitment_stock(
        city,
        plan,
        through_date=GameDate(1, 4, 1),
    )
    if first != second:
        raise RuntimeError("Recruitment stock was not deterministic")

    dwelling_a = keys["dwelling_a"]
    dwelling_b = keys["dwelling_b"]
    dwelling_c = keys["dwelling_c"]

    _expect(first, dwelling_a, GameDate(1, 1, 1), 5)
    _expect(first, dwelling_b, GameDate(1, 1, 1), 0)
    _expect(first, dwelling_c, GameDate(1, 1, 1), 2)

    _expect(first, dwelling_a, GameDate(1, 2, 1), 10)
    _expect(first, dwelling_c, GameDate(1, 2, 1), 4)
    _expect(first, dwelling_b, GameDate(1, 2, 2), 3)

    _expect(first, dwelling_a, GameDate(1, 3, 1), 17)
    _expect(first, dwelling_b, GameDate(1, 3, 1), 7)
    _expect(first, dwelling_c, GameDate(1, 3, 1), 7)

    _expect(first, dwelling_a, GameDate(1, 4, 1), 27)
    _expect(first, dwelling_b, GameDate(1, 4, 1), 13)
    _expect(first, dwelling_c, GameDate(1, 4, 1), 11)

    expected_daily_entries = (
        GameDate(1, 4, 1).day_index
        - plan.starting_date.day_index
        + 1
    ) * 3
    if len(first.entries) != expected_daily_entries:
        raise RuntimeError("Not every dwelling was tracked on every date")

    try:
        first.entries[0].available = 999
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise RuntimeError("Dwelling stock entry was mutable")

    try:
        first.entries = ()
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise RuntimeError("Recruitment stock result was mutable")

    if city.buildings != city_snapshot or plan != plan_snapshot:
        raise RuntimeError("Stock calculation mutated canonical inputs")

    print("Recruitment stock validation completed successfully.")
    print("Initial stock was granted on dwelling availability.")
    print("Weekly growth was granted only to previously built dwellings.")
    print("Wall modifiers affected later weekly grants, not same-day grants.")
    print("Fractional wall-modified growth rounded down.")
    print("Unrecruited stock accumulated across weeks.")
    print("Multiple dwellings were tracked independently on every date.")
    print("Repeated calculations were deterministic.")
    print("Results and source inputs remained immutable.")


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
