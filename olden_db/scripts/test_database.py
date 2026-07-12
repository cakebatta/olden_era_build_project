from __future__ import annotations

from olden_db.database import PLAYABLE_FACTIONS, load_default_game_data
from olden_db.models import ResourceCost, UnitFamily


def format_cost(cost: ResourceCost) -> str:
    parts = [
        f"{name}={amount}"
        for name, amount in cost.as_dict().items()
        if amount != 0
    ]
    return ", ".join(parts) if parts else "No cost"


def unique_unit_families(data) -> tuple[UnitFamily, ...]:
    families: list[UnitFamily] = []
    seen: set[tuple[str, str]] = set()

    for faction in PLAYABLE_FACTIONS:
        city = data.cities.city(faction)

        for building in city.buildings.values():
            family = building.unit_family
            if family is None:
                continue

            identity = (family.faction, family.dwelling_sid)
            if identity in seen:
                continue

            seen.add(identity)
            families.append(family)

    return tuple(
        sorted(
            families,
            key=lambda family: (
                family.faction,
                family.tier,
                family.dwelling_sid,
            ),
        )
    )


def find_family(
    families: tuple[UnitFamily, ...],
    *,
    base_sid: str,
) -> UnitFamily:
    for family in families:
        if family.base_sid == base_sid:
            return family

    raise RuntimeError(f"Could not find unit family for base SID {base_sid!r}")


def main() -> None:
    print("Loading connected Olden Era game database...\n")

    data = load_default_game_data()
    families = unique_unit_families(data)

    print("=" * 80)
    print("Connected database summary")
    print("=" * 80)
    print(f"Playable factions loaded: {data.faction_count}")
    print(f"Unit definitions loaded: {data.unit_count}")
    print(
        "Playable upgrade families verified: "
        f"{len(data.verified_upgrade_families)}"
    )
    print(f"Dwelling families connected to unit costs: {len(families)}")
    print()

    if data.faction_count != 6:
        raise RuntimeError(
            f"Expected 6 playable factions, found {data.faction_count}"
        )

    if data.unit_count != 149:
        raise RuntimeError(
            f"Expected 149 unit definitions, found {data.unit_count}"
        )

    if len(data.verified_upgrade_families) != 42:
        raise RuntimeError(
            "Expected 42 verified playable upgrade families, found "
            f"{len(data.verified_upgrade_families)}"
        )

    if len(families) != 42:
        raise RuntimeError(
            f"Expected 42 connected dwelling families, found {len(families)}"
        )

    print("Connected dwelling counts by faction")
    for faction in PLAYABLE_FACTIONS:
        count = sum(1 for family in families if family.faction == faction)
        print(f"  {faction:<10} {count:>2}")

        if count != 7:
            raise RuntimeError(
                f"Expected 7 dwelling families for {faction!r}, found {count}"
            )
    print()

    for family in families:
        base_definition = data.units.get(family.base_sid)
        upgrade_1_definition = data.units.get(family.upgrade_option_1_sid)
        upgrade_2_definition = data.units.get(family.upgrade_option_2_sid)

        if family.base_cost != base_definition.cost:
            raise RuntimeError(
                f"Base cost mismatch for {family.base_sid!r}"
            )

        if family.upgraded_cost != upgrade_1_definition.cost:
            raise RuntimeError(
                f"Upgrade cost mismatch for {family.upgrade_option_1_sid!r}"
            )

        if family.upgraded_cost != upgrade_2_definition.cost:
            raise RuntimeError(
                f"Upgrade cost mismatch for {family.upgrade_option_2_sid!r}"
            )

    angel = find_family(families, base_sid="angel")
    eldritch_flyer = find_family(families, base_sid="eldritch_flyer")

    print("Representative connected cost checks")
    print(f"  Angel base:              {format_cost(angel.base_cost)}")
    print(f"  Angel upgraded:          {format_cost(angel.upgraded_cost)}")
    print(
        "  Eldritch Flyer base:     "
        f"{format_cost(eldritch_flyer.base_cost)}"
    )
    print(
        "  Eldritch Flyer upgraded: "
        f"{format_cost(eldritch_flyer.upgraded_cost)}"
    )
    print()

    if angel.base_cost.gold != 2400 or angel.base_cost.gemstones != 1:
        raise RuntimeError(
            "Angel base recruitment cost did not match the expected values"
        )

    if eldritch_flyer.base_cost.gold != 450:
        raise RuntimeError(
            "Eldritch Flyer base recruitment cost did not match the expected value"
        )

    print("Database integration test completed successfully.")
    print("All playable dwellings are connected to correct unit recruitment costs.")


if __name__ == "__main__":
    main()
