from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .models import BuildingKey, BuildingLevel, FactionCity, GameDatabase, ResourceCost, UnitFamily

_TIER_PATTERN = re.compile(r"Build_Tier_(\d+)$", re.IGNORECASE)
_INCOME_EFFECT_TYPE = "sideRes"


class CityParseError(ValueError):
    """Raised when a faction-city JSON file has an unexpected structure."""


def load_json(path: str | Path) -> Any:
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8-sig") as file:
            return json.load(file)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise CityParseError(
            f"Invalid JSON in {source}: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def parse_city_file(path: str | Path, *, unit_costs: Mapping[str, ResourceCost] | None = None) -> FactionCity:
    source = Path(path)
    data = load_json(source)
    raw_cities = data.get("array") if isinstance(data, dict) else None
    if not isinstance(raw_cities, list) or not raw_cities:
        raise CityParseError(f"{source} must contain a non-empty top-level 'array' list")
    if len(raw_cities) != 1:
        raise CityParseError(f"{source} contains {len(raw_cities)} city records; expected 1")
    raw_city = raw_cities[0]
    if not isinstance(raw_city, dict):
        raise CityParseError(f"{source}: city record must be a JSON object")

    faction = _required_string(raw_city, "fraction", source)
    city_id = _required_string(raw_city, "id", source)
    city = FactionCity(faction=faction, city_id=city_id)
    for category, raw_buildings in raw_city.items():
        if not isinstance(raw_buildings, list):
            continue
        for raw_building in raw_buildings:
            if not _looks_like_building(raw_building):
                continue
            for building in _parse_building(
                raw_building,
                faction=faction,
                category=category,
                source=source,
                unit_costs=unit_costs,
            ):
                city.add_building(building)
    if not city.buildings:
        raise CityParseError(f"{source}: no building definitions were found")
    return city


def parse_city_files(paths: Iterable[str | Path], *, unit_costs: Mapping[str, ResourceCost] | None = None) -> GameDatabase:
    database = GameDatabase()
    for path in paths:
        database.add_city(parse_city_file(path, unit_costs=unit_costs))
    return database


def parse_city_directory(directory: str | Path, *, pattern: str = "*_city.json", unit_costs: Mapping[str, ResourceCost] | None = None) -> GameDatabase:
    root = Path(directory)
    paths = sorted(root.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No city files matching {pattern!r} were found in {root}")
    return parse_city_files(paths, unit_costs=unit_costs)


def _looks_like_building(value: object) -> bool:
    return isinstance(value, dict) and isinstance(value.get("sid"), str) and isinstance(value.get("parametersPerLevel"), list)


def _parse_building(raw: Mapping[str, Any], *, faction: str, category: str, source: Path, unit_costs: Mapping[str, ResourceCost] | None) -> list[BuildingLevel]:
    sid = _required_string(raw, "sid", source)
    parameters = raw.get("parametersPerLevel")
    if not isinstance(parameters, list) or not parameters:
        raise CityParseError(f"{source}: {sid!r} must have a non-empty parametersPerLevel list")
    names = raw.get("names", [])
    if names is None:
        names = []
    if not isinstance(names, list):
        raise CityParseError(f"{source}: {sid!r}.names must be a list")

    incomes = _parse_income_levels(raw.get("bonusesPerLevel"), level_count=len(parameters), source=source, sid=sid)
    is_constructed_on_start = bool(raw.get("isConstructedOnStart", False))
    level_on_start = _positive_int(raw.get("levelOnStart", 1), context=f"{source}: {sid!r}.levelOnStart")
    scene_slot_value = raw.get("sceneSlot")
    scene_slot = str(scene_slot_value) if scene_slot_value is not None else None
    unit_family = _parse_unit_family(raw, faction=faction, dwelling_sid=sid, source=source, unit_costs=unit_costs)

    parsed: list[BuildingLevel] = []
    for index, raw_level in enumerate(parameters):
        level = index + 1
        if not isinstance(raw_level, dict):
            raise CityParseError(f"{source}: {sid!r} level {level} must be a JSON object")
        name_key = str(names[index]) if index < len(names) and names[index] is not None else None
        prerequisites = _parse_prerequisites(
            raw_level.get("prevBuildings", []),
            faction=faction,
            source=source,
            owner_sid=sid,
            owner_level=level,
        )
        costs = raw_level.get("costs", [])
        if not isinstance(costs, list):
            raise CityParseError(f"{source}: {sid!r} level {level}.costs must be a list")
        try:
            cost = ResourceCost.from_entries(costs)
        except ValueError as exc:
            raise CityParseError(f"{source}: invalid cost for {sid!r} level {level}: {exc}") from exc
        node_x, node_y = _parse_node_position(raw_level.get("nodePos"), source=source, sid=sid, level=level)
        try:
            parsed.append(BuildingLevel(
                key=BuildingKey(faction=faction, sid=sid, level=level),
                category=category,
                name_key=name_key,
                scene_slot=scene_slot,
                cost=cost,
                prerequisites=prerequisites,
                constructed_on_start=is_constructed_on_start and level <= level_on_start,
                unit_family=unit_family,
                node_x=node_x,
                node_y=node_y,
                income=incomes[index],
            ))
        except ValueError as exc:
            raise CityParseError(f"{source}: invalid building data for {sid!r} level {level}: {exc}") from exc
    return parsed


def _parse_income_levels(raw_levels: object, *, level_count: int, source: Path, sid: str) -> tuple[ResourceCost, ...]:
    if raw_levels is None:
        return tuple(ResourceCost() for _ in range(level_count))
    if not isinstance(raw_levels, list):
        raise CityParseError(f"{source}: {sid!r} level 1 bonusesPerLevel must be a list")
    if len(raw_levels) != level_count:
        raise CityParseError(
            f"{source}: {sid!r}.bonusesPerLevel contains {len(raw_levels)} levels; expected {level_count}"
        )

    result: list[ResourceCost] = []
    for level, raw_level in enumerate(raw_levels, start=1):
        context = f"{source}: {sid!r} level {level}"
        if not isinstance(raw_level, dict):
            raise CityParseError(f"{context}.bonusesPerLevel entry must be an object")
        bonuses = raw_level.get("bonuses")
        if not isinstance(bonuses, list):
            raise CityParseError(f"{context}.bonuses must be a list")
        entries: list[dict[str, object]] = []
        for bonus in bonuses:
            if not isinstance(bonus, dict):
                raise CityParseError(f"{context} bonus must be an object")
            if bonus.get("type") != _INCOME_EFFECT_TYPE:
                continue
            parameters = bonus.get("parameters")
            if not isinstance(parameters, list) or len(parameters) < 2:
                raise CityParseError(f"{context} contains malformed sideRes parameters: {parameters!r}")
            resource, amount = parameters[0], parameters[1]
            if not isinstance(resource, str) or not resource.strip():
                raise CityParseError(f"{context} contains an invalid income resource: {resource!r}")
            try:
                parsed_amount = int(amount)
            except (TypeError, ValueError) as exc:
                raise CityParseError(f"{context} contains invalid income amount: {amount!r}") from exc
            entries.append({"name": resource.strip(), "cost": parsed_amount})
        try:
            income = ResourceCost.from_entries(entries)
        except ValueError as exc:
            raise CityParseError(f"{context} contains invalid baseline income: {exc}") from exc
        if any(value < 0 for value in income.as_dict().values()):
            raise CityParseError(f"{context} contains negative baseline income: {income.as_dict()}")
        result.append(income)
    return tuple(result)


def _parse_prerequisites(raw_prerequisites: object, *, faction: str, source: Path, owner_sid: str, owner_level: int) -> tuple[BuildingKey, ...]:
    if raw_prerequisites is None:
        return ()
    if not isinstance(raw_prerequisites, list):
        raise CityParseError(f"{source}: {owner_sid!r} level {owner_level}.prevBuildings must be a list")
    parsed: list[BuildingKey] = []
    for raw in raw_prerequisites:
        if not isinstance(raw, dict):
            raise CityParseError(f"{source}: prerequisite for {owner_sid!r} level {owner_level} must be an object")
        prerequisite_sid = _required_string(raw, "sid", source)
        prerequisite_level = _positive_int(
            raw.get("level"),
            context=f"{source}: prerequisite {prerequisite_sid!r} for {owner_sid!r} level {owner_level}",
        )
        parsed.append(BuildingKey(faction=faction, sid=prerequisite_sid, level=prerequisite_level))
    if len(set(parsed)) != len(parsed):
        raise CityParseError(f"{source}: duplicate prerequisites for {owner_sid!r} level {owner_level}")
    return tuple(parsed)


def _parse_unit_family(raw_building: Mapping[str, Any], *, faction: str, dwelling_sid: str, source: Path, unit_costs: Mapping[str, ResourceCost] | None) -> UnitFamily | None:
    raw_hire = raw_building.get("unitsHire")
    if raw_hire is None:
        return None
    if not isinstance(raw_hire, dict):
        raise CityParseError(f"{source}: {dwelling_sid!r}.unitsHire must be an object")
    raw_units = raw_hire.get("units")
    if not isinstance(raw_units, list) or not raw_units:
        raise CityParseError(f"{source}: {dwelling_sid!r}.unitsHire.units must be non-empty")
    if len(raw_units) != 1:
        raise CityParseError(f"{source}: {dwelling_sid!r} contains {len(raw_units)} unit families; the current model expects exactly 1")
    raw_family = raw_units[0]
    if not isinstance(raw_family, dict):
        raise CityParseError(f"{source}: {dwelling_sid!r} unit-family entry must be an object")
    raw_sids = raw_family.get("sids")
    if not isinstance(raw_sids, list) or len(raw_sids) != 3:
        raise CityParseError(f"{source}: {dwelling_sid!r} must list exactly three unit SIDs")
    sids = tuple(str(value) for value in raw_sids)
    weekly_growth = _nonnegative_int(raw_family.get("weeklyIncrement"), context=f"{source}: {dwelling_sid!r}.weeklyIncrement")
    tier = _tier_from_dwelling_sid(dwelling_sid, source)
    base_cost = ResourceCost()
    upgraded_cost = ResourceCost()
    if unit_costs is not None:
        missing = [sid for sid in sids if sid not in unit_costs]
        if missing:
            raise CityParseError(f"{source}: missing unit-cost definitions for {missing}")
        base_cost = unit_costs[sids[0]]
        option_1_cost = unit_costs[sids[1]]
        option_2_cost = unit_costs[sids[2]]
        if option_1_cost != option_2_cost:
            raise CityParseError(f"{source}: upgrade costs differ for {sids[1]!r} and {sids[2]!r}")
        upgraded_cost = option_1_cost
    return UnitFamily(
        faction=faction,
        tier=tier,
        dwelling_sid=dwelling_sid,
        base_sid=sids[0],
        upgrade_option_1_sid=sids[1],
        upgrade_option_2_sid=sids[2],
        weekly_growth=weekly_growth,
        base_cost=base_cost,
        upgraded_cost=upgraded_cost,
    )


def _tier_from_dwelling_sid(sid: str, source: Path) -> int:
    match = _TIER_PATTERN.fullmatch(sid)
    if match is None:
        raise CityParseError(f"{source}: cannot infer unit tier from dwelling SID {sid!r}")
    return int(match.group(1))


def _parse_node_position(raw_node: object, *, source: Path, sid: str, level: int) -> tuple[int | None, int | None]:
    if raw_node is None:
        return None, None
    if not isinstance(raw_node, dict):
        raise CityParseError(f"{source}: {sid!r} level {level}.nodePos must be an object")
    x_value = raw_node.get("xPos")
    y_value = raw_node.get("yPos")
    return (int(x_value) if x_value is not None else None, int(y_value) if y_value is not None else None)


def _required_string(mapping: Mapping[str, Any], key: str, source: Path) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise CityParseError(f"{source}: required field {key!r} must be a non-empty string")
    return value


def _positive_int(value: object, *, context: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CityParseError(f"{context} must be an integer") from exc
    if parsed < 1:
        raise CityParseError(f"{context} must be at least 1")
    return parsed


def _nonnegative_int(value: object, *, context: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CityParseError(f"{context} must be an integer") from exc
    if parsed < 0:
        raise CityParseError(f"{context} cannot be negative")
    return parsed
