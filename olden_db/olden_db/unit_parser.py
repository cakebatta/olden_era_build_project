from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping
from zipfile import ZipFile

from .models import ResourceCost


class UnitParseError(ValueError):
    """Raised when a unit-logic file has an unexpected structure."""


class DuplicateUnitError(UnitParseError):
    """Raised when two unit files define the same SID."""


class UpgradeCostMismatchError(UnitParseError):
    """Raised when two upgrade branches have different recruitment costs."""


@dataclass(frozen=True, slots=True)
class UnitDefinition:
    """Economic and identity data extracted from one unit-logic record."""

    sid: str
    faction: str
    tier: int
    cost: ResourceCost
    upgrade_sid: str | None
    source: str

    def __post_init__(self) -> None:
        if not self.sid:
            raise ValueError("unit SID cannot be empty")
        if not self.faction:
            raise ValueError("unit faction cannot be empty")
        if self.tier < 1:
            raise ValueError("unit tier must be at least 1")


@dataclass(frozen=True, slots=True)
class UnitCatalog:
    """Lookup container for all parsed unit definitions."""

    units: dict[str, UnitDefinition]

    def __post_init__(self) -> None:
        if len(self.units) != len(set(self.units)):
            raise ValueError("unit catalog contains duplicate SIDs")

    def get(self, sid: str) -> UnitDefinition:
        try:
            return self.units[sid]
        except KeyError as exc:
            raise KeyError(f"Unknown unit SID: {sid!r}") from exc

    def cost_lookup(self) -> dict[str, ResourceCost]:
        """Return the SID-to-cost mapping expected by the city parser."""
        return {
            sid: definition.cost
            for sid, definition in self.units.items()
        }

    def faction_units(self, faction: str) -> tuple[UnitDefinition, ...]:
        """Return all units for one faction in stable tier/SID order."""
        return tuple(
            sorted(
                (
                    definition
                    for definition in self.units.values()
                    if definition.faction == faction
                ),
                key=lambda definition: (definition.tier, definition.sid),
            )
        )


def parse_unit_file(path: str | Path) -> UnitDefinition:
    """Parse one UTF-8 unit-logic JSON file."""
    source = Path(path)

    try:
        with source.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise UnitParseError(
            f"Invalid JSON in {source}: line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc

    return _parse_unit_document(data, source=str(source))


def parse_unit_directory(
    directory: str | Path,
    *,
    pattern: str = "*.json",
) -> UnitCatalog:
    """Recursively parse all matching unit JSON files in a directory."""
    root = Path(directory)
    paths = sorted(path for path in root.rglob(pattern) if path.is_file())

    if not paths:
        raise FileNotFoundError(
            f"No unit files matching {pattern!r} were found in {root}"
        )

    return _build_catalog(
        parse_unit_file(path)
        for path in paths
    )


def parse_unit_zip(
    path: str | Path,
    *,
    member_suffix: str = ".json",
) -> UnitCatalog:
    """Parse every matching unit JSON member directly from a ZIP archive."""
    source = Path(path)

    with ZipFile(source) as archive:
        members = sorted(
            name
            for name in archive.namelist()
            if not name.endswith("/")
            and name.lower().endswith(member_suffix.lower())
        )

        if not members:
            raise FileNotFoundError(
                f"No unit files ending in {member_suffix!r} were found "
                f"inside {source}"
            )

        definitions: list[UnitDefinition] = []

        for member in members:
            try:
                raw_bytes = archive.read(member)
                data = json.loads(raw_bytes.decode("utf-8-sig"))
            except UnicodeDecodeError as exc:
                raise UnitParseError(
                    f"{source}!{member} is not valid UTF-8 text"
                ) from exc
            except json.JSONDecodeError as exc:
                raise UnitParseError(
                    f"Invalid JSON in {source}!{member}: line {exc.lineno}, "
                    f"column {exc.colno}: {exc.msg}"
                ) from exc

            definitions.append(
                _parse_unit_document(
                    data,
                    source=f"{source}!{PurePosixPath(member)}",
                )
            )

    return _build_catalog(definitions)


def verify_upgrade_branch_costs(
    catalog: UnitCatalog,
    *,
    factions: Iterable[str] | None = None,
) -> tuple[tuple[str, str, str], ...]:
    """
    Verify that each base unit's two upgrade branches have equal costs.

    Returns tuples of:
        (base_sid, upgrade_option_1_sid, upgrade_option_2_sid)

    Only complete three-unit families are returned. A family with exactly one
    upgrade branch raises UnitParseError.
    """
    allowed_factions = set(factions) if factions is not None else None
    verified: list[tuple[str, str, str]] = []

    for definition in sorted(
        catalog.units.values(),
        key=lambda unit: (unit.faction, unit.tier, unit.sid),
    ):
        if "_upg" in definition.sid:
            continue

        if (
            allowed_factions is not None
            and definition.faction not in allowed_factions
        ):
            continue

        option_1_sid = f"{definition.sid}_upg"
        option_2_sid = f"{definition.sid}_upg_alt"

        has_option_1 = option_1_sid in catalog.units
        has_option_2 = option_2_sid in catalog.units

        if not has_option_1 and not has_option_2:
            continue

        if has_option_1 != has_option_2:
            missing_sid = option_2_sid if has_option_1 else option_1_sid
            raise UnitParseError(
                f"Incomplete upgrade family for {definition.sid!r}: "
                f"missing {missing_sid!r}"
            )

        option_1 = catalog.units[option_1_sid]
        option_2 = catalog.units[option_2_sid]

        if option_1.faction != definition.faction:
            raise UnitParseError(
                f"Faction mismatch in upgrade family {definition.sid!r}"
            )
        if option_2.faction != definition.faction:
            raise UnitParseError(
                f"Faction mismatch in upgrade family {definition.sid!r}"
            )
        if option_1.tier != definition.tier or option_2.tier != definition.tier:
            raise UnitParseError(
                f"Tier mismatch in upgrade family {definition.sid!r}"
            )

        if option_1.cost != option_2.cost:
            raise UpgradeCostMismatchError(
                f"Upgrade costs differ for {option_1_sid!r} and "
                f"{option_2_sid!r}: "
                f"{option_1.cost.as_dict()} != {option_2.cost.as_dict()}"
            )

        verified.append(
            (definition.sid, option_1_sid, option_2_sid)
        )

    return tuple(verified)


def _build_catalog(
    definitions: Iterable[UnitDefinition],
) -> UnitCatalog:
    units: dict[str, UnitDefinition] = {}

    for definition in definitions:
        if definition.sid in units:
            previous = units[definition.sid]
            raise DuplicateUnitError(
                f"Duplicate unit SID {definition.sid!r} in "
                f"{previous.source!r} and {definition.source!r}"
            )

        units[definition.sid] = definition

    return UnitCatalog(units=units)


def _parse_unit_document(
    data: object,
    *,
    source: str,
) -> UnitDefinition:
    if not isinstance(data, dict):
        raise UnitParseError(f"{source}: top-level JSON value must be an object")

    raw_array = data.get("array")
    if not isinstance(raw_array, list) or len(raw_array) != 1:
        count = len(raw_array) if isinstance(raw_array, list) else "non-list"
        raise UnitParseError(
            f"{source}: top-level 'array' must contain exactly one record; "
            f"found {count}"
        )

    raw = raw_array[0]
    if not isinstance(raw, dict):
        raise UnitParseError(f"{source}: unit record must be a JSON object")

    sid = _required_string(raw, "id", source)
    faction = _required_string(raw, "fraction", source)
    tier = _positive_int(raw.get("tier"), context=f"{source}: tier")

    raw_unit_cost = raw.get("unitCost")
    if not isinstance(raw_unit_cost, dict):
        raise UnitParseError(f"{source}: unitCost must be an object")

    raw_costs = raw_unit_cost.get("costResArray")
    if not isinstance(raw_costs, list):
        raise UnitParseError(
            f"{source}: unitCost.costResArray must be a list"
        )

    try:
        cost = ResourceCost.from_entries(raw_costs)
    except ValueError as exc:
        raise UnitParseError(
            f"{source}: invalid recruitment cost for {sid!r}: {exc}"
        ) from exc

    raw_upgrade_sid = raw.get("upgradeSid")
    if raw_upgrade_sid is None:
        upgrade_sid = None
    elif isinstance(raw_upgrade_sid, str) and raw_upgrade_sid:
        upgrade_sid = raw_upgrade_sid
    else:
        raise UnitParseError(
            f"{source}: upgradeSid must be a non-empty string or absent"
        )

    return UnitDefinition(
        sid=sid,
        faction=faction,
        tier=tier,
        cost=cost,
        upgrade_sid=upgrade_sid,
        source=source,
    )


def _required_string(
    mapping: Mapping[str, Any],
    key: str,
    source: str,
) -> str:
    value = mapping.get(key)

    if not isinstance(value, str) or not value:
        raise UnitParseError(
            f"{source}: required field {key!r} must be a non-empty string"
        )

    return value


def _positive_int(value: object, *, context: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise UnitParseError(f"{context} must be an integer") from exc

    if parsed < 1:
        raise UnitParseError(f"{context} must be at least 1")

    return parsed
