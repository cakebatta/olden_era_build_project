from __future__ import annotations

import argparse
from pathlib import Path

from olden_db.models import ResourceCost
from olden_db.paths import PROJECT_ROOT, require_unit_logic_source
from olden_db.unit_parser import (
    UnitCatalog,
    parse_unit_directory,
    parse_unit_zip,
    verify_upgrade_branch_costs,
)


PLAYABLE_FACTIONS = (
    "demon",
    "dungeon",
    "human",
    "nature",
    "undead",
    "unfrozen",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Parse Olden Era unit logic, verify upgrade costs, and print a "
            "readable economic summary."
        )
    )
    parser.add_argument(
        "--source",
        default=None,
        help=(
            "Optional path to a unit-logic ZIP or extracted directory. "
            "Relative paths are resolved from the project root."
        ),
    )
    parser.add_argument(
        "--faction",
        choices=PLAYABLE_FACTIONS,
        help="Optionally print detailed unit data for one playable faction.",
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Print detailed unit data for all playable factions.",
    )
    return parser.parse_args()


def format_cost(cost: ResourceCost) -> str:
    parts = [
        f"{name}={amount}"
        for name, amount in cost.as_dict().items()
        if amount != 0
    ]
    return ", ".join(parts) if parts else "No cost"


def load_catalog(source: Path) -> UnitCatalog:
    if source.is_dir():
        return parse_unit_directory(source)

    if source.is_file() and source.suffix.lower() == ".zip":
        return parse_unit_zip(source)

    raise FileNotFoundError(
        f"Unit source must be an existing ZIP file or directory: {source}"
    )


def print_faction_details(catalog: UnitCatalog, faction: str) -> None:
    units = catalog.faction_units(faction)

    print("=" * 80)
    print(f"Faction: {faction}")
    print(f"Unit definitions: {len(units)}")
    print("=" * 80)
    print()

    by_tier: dict[int, list] = {}

    for unit in units:
        by_tier.setdefault(unit.tier, []).append(unit)

    for tier in sorted(by_tier):
        tier_units = sorted(
            by_tier[tier],
            key=lambda unit: unit.sid,
        )

        print(f"Tier {tier}")

        for unit in tier_units:
            print(f"  {unit.sid}")
            print(f"    Recruitment cost: {format_cost(unit.cost)}")

            if unit.upgrade_sid:
                print(f"    upgradeSid: {unit.upgrade_sid}")
            else:
                print("    upgradeSid: None")

        print()


def main() -> None:
    args = parse_arguments()

    if args.source is None:
        source = require_unit_logic_source()
    else:
        source = Path(args.source)
        if not source.is_absolute():
            source = PROJECT_ROOT / source

    print(f"Loading unit logic from:\n  {source}\n")

    catalog = load_catalog(source)

    verified_families = verify_upgrade_branch_costs(
        catalog,
        factions=PLAYABLE_FACTIONS,
    )

    print("=" * 80)
    print("Unit parser summary")
    print("=" * 80)
    print(f"Total unit definitions: {len(catalog.units)}")
    print(f"Playable upgrade families verified: {len(verified_families)}")
    print()

    print("Playable faction counts")
    for faction in PLAYABLE_FACTIONS:
        print(f"  {faction:<10} {len(catalog.faction_units(faction)):>3}")
    print()

    print("Representative cost checks")
    representative_sids = (
        "angel",
        "angel_upg",
        "angel_upg_alt",
        "eldritch_flyer",
        "trick_demon",
    )

    for sid in representative_sids:
        if sid in catalog.units:
            unit = catalog.get(sid)
            print(f"  {sid:<24} {format_cost(unit.cost)}")
    print()

    angel_upgrade_1 = catalog.get("angel_upg").cost
    angel_upgrade_2 = catalog.get("angel_upg_alt").cost

    if angel_upgrade_1 != angel_upgrade_2:
        raise RuntimeError("Angel upgrade branch costs do not match")

    if len(set(catalog.units)) != len(catalog.units):
        raise RuntimeError("Duplicate unit SIDs were found")

    if args.show_all:
        factions_to_print = PLAYABLE_FACTIONS
    elif args.faction:
        factions_to_print = (args.faction,)
    else:
        factions_to_print = ()

    for faction in factions_to_print:
        print_faction_details(catalog, faction)

    print("Unit parser test completed successfully.")
    print("All playable upgrade branch costs are equal and internally consistent.")


if __name__ == "__main__":
    main()
