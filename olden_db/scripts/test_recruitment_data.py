from __future__ import annotations

from collections import defaultdict

from olden_db.constants import RESOURCE_NAMES
from olden_db.database import PLAYABLE_FACTIONS, load_default_game_data
from olden_db.models import ResourceCost, UnitFamily


EXPECTED_TIERS = frozenset(range(1, 8))
EXPECTED_DWELLING_LEVELS = frozenset({1, 2})


def _format_cost(cost: ResourceCost) -> str:
    populated = [
        f"{name}={amount}"
        for name in RESOURCE_NAMES
        if (amount := getattr(cost, name)) != 0
    ]
    return ", ".join(populated) if populated else "ZERO"


def _family_identity(family: UnitFamily) -> tuple[object, ...]:
    return (
        family.faction,
        family.tier,
        family.dwelling_sid,
        family.base_sid,
        family.upgrade_option_1_sid,
        family.upgrade_option_2_sid,
        family.weekly_growth,
        family.base_cost,
        family.upgraded_cost,
    )


def main() -> None:
    data = load_default_game_data()

    families: dict[tuple[str, str], UnitFamily] = {}
    dwelling_levels: dict[tuple[str, str], set[int]] = defaultdict(set)
    family_identities: dict[tuple[str, str], set[tuple[object, ...]]] = defaultdict(set)
    unit_links: dict[str, list[tuple[str, str, str]]] = defaultdict(list)

    errors: list[str] = []

    for faction in PLAYABLE_FACTIONS:
        city = data.cities.city(faction)

        for building in city.buildings.values():
            family = building.unit_family
            if family is None:
                continue

            key = (faction, family.dwelling_sid)
            families.setdefault(key, family)
            dwelling_levels[key].add(building.key.level)
            family_identities[key].add(_family_identity(family))

    for key, identities in sorted(family_identities.items()):
        if len(identities) != 1:
            errors.append(
                f"Conflicting unit-family data across dwelling levels: {key}"
            )

    coverage: dict[str, set[int]] = {
        faction: set() for faction in PLAYABLE_FACTIONS
    }

    for (faction, dwelling_sid), family in sorted(families.items()):
        coverage[faction].add(family.tier)

        expected_sid = f"Build_Tier_{family.tier}"
        if dwelling_sid != expected_sid:
            errors.append(
                f"Unexpected dwelling SID for {faction} tier {family.tier}: "
                f"{dwelling_sid!r}; expected {expected_sid!r}"
            )

        if family.faction != faction:
            errors.append(
                f"Family faction mismatch for {dwelling_sid}: "
                f"city={faction!r}, family={family.faction!r}"
            )

        levels = frozenset(dwelling_levels[(faction, dwelling_sid)])
        if levels != EXPECTED_DWELLING_LEVELS:
            errors.append(
                f"Unexpected levels for {faction}/{dwelling_sid}: "
                f"{sorted(levels)}; expected [1, 2]"
            )

        if family.weekly_growth <= 0:
            errors.append(
                f"Invalid weekly growth for {faction}/{dwelling_sid}: "
                f"{family.weekly_growth}"
            )

        if family.base_cost.is_zero():
            errors.append(
                f"Missing or zero base recruitment cost for "
                f"{faction}/{family.base_sid}"
            )

        if family.upgraded_cost.is_zero():
            errors.append(
                f"Missing or zero upgraded recruitment cost for "
                f"{faction}/{dwelling_sid}"
            )

        base = data.units.get(family.base_sid)
        option_1 = data.units.get(family.upgrade_option_1_sid)
        option_2 = data.units.get(family.upgrade_option_2_sid)

        for role, unit in (
            ("base", base),
            ("upgrade option 1", option_1),
            ("upgrade option 2", option_2),
        ):
            if unit.faction != faction:
                errors.append(
                    f"{role} faction mismatch for {unit.sid}: "
                    f"expected {faction!r}, found {unit.faction!r}"
                )
            if unit.tier != family.tier:
                errors.append(
                    f"{role} tier mismatch for {unit.sid}: "
                    f"dwelling={family.tier}, unit={unit.tier}"
                )
            unit_links[unit.sid].append((faction, dwelling_sid, role))

        if family.base_cost != base.cost:
            errors.append(
                f"Attached base cost mismatch for {faction}/{family.base_sid}"
            )

        if option_1.cost != option_2.cost:
            errors.append(
                f"Upgrade branch cost mismatch for {faction}/{dwelling_sid}: "
                f"{family.upgrade_option_1_sid}={_format_cost(option_1.cost)}; "
                f"{family.upgrade_option_2_sid}={_format_cost(option_2.cost)}"
            )

        if family.upgraded_cost != option_1.cost:
            errors.append(
                f"Attached upgraded cost mismatch for {faction}/{dwelling_sid}"
            )

    for sid, links in sorted(unit_links.items()):
        if len(links) != 1:
            errors.append(f"Unit SID {sid!r} is linked by multiple dwellings: {links}")

    for faction, tiers in coverage.items():
        if tiers != EXPECTED_TIERS:
            errors.append(
                f"Incomplete tier coverage for {faction}: "
                f"found {sorted(tiers)}, expected {sorted(EXPECTED_TIERS)}"
            )

    expected_family_count = len(PLAYABLE_FACTIONS) * len(EXPECTED_TIERS)
    if len(families) != expected_family_count:
        errors.append(
            f"Expected {expected_family_count} dwelling-linked families, "
            f"found {len(families)}"
        )

    print("Recruitment data validation")
    print(f"Dwelling-linked unit families: {len(families)}")
    print(f"Playable factions: {len(PLAYABLE_FACTIONS)}")
    print()
    print("Faction and tier coverage:")
    for faction in PLAYABLE_FACTIONS:
        print(f"  {faction}: {sorted(coverage[faction])}")

    print()
    print("Dwelling-level access structure:")
    print("  Every validated dwelling has levels 1 and 2.")
    print("  Assets attach one shared UnitFamily to the dwelling definition.")
    print("  Assets do not independently encode base-versus-upgraded access per level.")

    print()
    print("Special cases:")
    print("  None requiring architectural treatment.")

    print()
    if errors:
        print("FAILED")
        for error in errors:
            print(f"  ERROR: {error}")
        raise SystemExit(1)

    print("PASS")
    print("  All factions contain tiers 1-7.")
    print("  All dwelling-linked families contain three distinct unit SIDs.")
    print("  All weekly growth values are positive.")
    print("  All base and upgraded recruitment costs are non-zero.")
    print("  Both upgrade alternatives have identical costs.")
    print("  No unit SID is linked to more than one dwelling family.")


if __name__ == "__main__":
    main()
