from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .models import GameDatabase
from .parser import parse_city_directory
from .paths import require_city_directory, require_unit_logic_source
from .unit_parser import (
    UnitCatalog,
    parse_unit_directory,
    parse_unit_zip,
    verify_upgrade_branch_costs,
)


PLAYABLE_FACTIONS: tuple[str, ...] = (
    "demon",
    "dungeon",
    "human",
    "nature",
    "undead",
    "unfrozen",
)


class DatabaseLoadError(ValueError):
    """Raised when the combined game database cannot be assembled."""


@dataclass(frozen=True, slots=True)
class LoadedGameData:
    """
    Fully connected in-memory game data.

    `cities` contains building and dwelling data. Every dwelling UnitFamily is
    populated with recruitment costs sourced from `units`.
    """

    cities: GameDatabase
    units: UnitCatalog
    verified_upgrade_families: tuple[tuple[str, str, str], ...]

    @property
    def faction_count(self) -> int:
        return len(self.cities.cities)

    @property
    def unit_count(self) -> int:
        return len(self.units.units)


def load_game_data(
    city_directory: str | Path,
    unit_source: str | Path,
    *,
    playable_factions: Iterable[str] = PLAYABLE_FACTIONS,
) -> LoadedGameData:
    """
    Load unit logic, verify upgrade branches, then parse all faction cities.

    Unit costs are passed into the existing city parser, which attaches:
    - base recruitment cost;
    - shared upgraded recruitment cost;
    to every dwelling's UnitFamily.
    """
    city_root = Path(city_directory)
    unit_path = Path(unit_source)

    unit_catalog = _load_unit_catalog(unit_path)

    factions = tuple(playable_factions)
    verified_families = verify_upgrade_branch_costs(
        unit_catalog,
        factions=factions,
    )

    cities = parse_city_directory(
        city_root,
        unit_costs=unit_catalog.cost_lookup(),
    )

    _validate_connected_data(
        cities,
        unit_catalog,
        playable_factions=factions,
    )

    return LoadedGameData(
        cities=cities,
        units=unit_catalog,
        verified_upgrade_families=verified_families,
    )


def load_default_game_data() -> LoadedGameData:
    """Load the project's canonical city and unit-logic sources."""
    return load_game_data(
        require_city_directory(),
        require_unit_logic_source(),
    )


def _load_unit_catalog(source: Path) -> UnitCatalog:
    if source.is_dir():
        return parse_unit_directory(source)

    if source.is_file() and source.suffix.lower() == ".zip":
        return parse_unit_zip(source)

    raise FileNotFoundError(
        "Unit source must be an existing ZIP file or directory:\n"
        f"  {source}"
    )


def _validate_connected_data(
    cities: GameDatabase,
    units: UnitCatalog,
    *,
    playable_factions: tuple[str, ...],
) -> None:
    """Confirm every playable dwelling was connected to correct unit costs."""
    missing_factions = [
        faction
        for faction in playable_factions
        if faction not in cities.cities
    ]
    if missing_factions:
        raise DatabaseLoadError(
            f"Missing playable faction cities: {missing_factions}"
        )

    dwelling_count = 0

    for faction in playable_factions:
        city = cities.city(faction)
        seen_families: set[str] = set()

        for building in city.buildings.values():
            family = building.unit_family
            if family is None or family.dwelling_sid in seen_families:
                continue

            seen_families.add(family.dwelling_sid)
            dwelling_count += 1

            referenced_sids = (
                family.base_sid,
                family.upgrade_option_1_sid,
                family.upgrade_option_2_sid,
            )

            for sid in referenced_sids:
                definition = units.get(sid)

                if definition.faction != faction:
                    raise DatabaseLoadError(
                        f"Faction mismatch for unit {sid!r}: "
                        f"city={faction!r}, unit={definition.faction!r}"
                    )

                if definition.tier != family.tier:
                    raise DatabaseLoadError(
                        f"Tier mismatch for unit {sid!r}: "
                        f"dwelling={family.tier}, unit={definition.tier}"
                    )

            if family.base_cost != units.get(family.base_sid).cost:
                raise DatabaseLoadError(
                    f"Base cost was not attached correctly for "
                    f"{family.base_sid!r}"
                )

            expected_upgrade_cost = units.get(
                family.upgrade_option_1_sid
            ).cost

            if family.upgraded_cost != expected_upgrade_cost:
                raise DatabaseLoadError(
                    f"Upgrade cost was not attached correctly for "
                    f"{family.dwelling_sid!r}"
                )

    expected_dwelling_count = len(playable_factions) * 7
    if dwelling_count != expected_dwelling_count:
        raise DatabaseLoadError(
            f"Expected {expected_dwelling_count} playable dwelling families, "
            f"found {dwelling_count}"
        )
