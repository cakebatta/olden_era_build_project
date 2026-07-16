from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from olden_db.constants import RESOURCE_NAMES
from olden_db.database import PLAYABLE_FACTIONS, load_default_game_data
from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.parser import CityParseError, parse_city_directory, parse_city_file
from olden_db.paths import require_city_directory

EXPECTED_MAIN_INCOME = {
    1: ResourceCost(gold=500),
    2: ResourceCost(gold=750),
    3: ResourceCost(gold=1000),
}


def main() -> None:
    city_directory = require_city_directory()
    first = parse_city_directory(city_directory)
    second = parse_city_directory(city_directory)
    if first != second:
        raise RuntimeError("Repeated city parsing was not deterministic")

    normalized_rows: list[tuple[str, str, int, ResourceCost]] = []
    for faction in PLAYABLE_FACTIONS:
        city = first.city(faction)
        for level, expected in EXPECTED_MAIN_INCOME.items():
            building = city.get("Build_Main", level)
            if building.income != expected:
                raise RuntimeError(
                    f"Unexpected income for {faction}/Build_Main level {level}: "
                    f"expected {expected}, got {building.income}"
                )
            _assert_only_gold(building.income, expected.gold)
            normalized_rows.append((faction, "Build_Main", level, building.income))

        for sid in ("Build_Tier_1", "Build_Wall", "Build_Tavern", "Build_Magic_Guild"):
            candidate = next(
                (building for building in city.buildings.values() if building.key.sid == sid),
                None,
            )
            if candidate is not None and candidate.income != ResourceCost():
                raise RuntimeError(
                    f"Non-income building received income: {candidate.key}={candidate.income}"
                )

    loaded = load_default_game_data()
    for faction in PLAYABLE_FACTIONS:
        for level, expected in EXPECTED_MAIN_INCOME.items():
            actual = loaded.cities.city(faction).get("Build_Main", level).income
            if actual != expected:
                raise RuntimeError("Income did not survive database integration")

    _check_model_default_and_validation()
    _check_malformed_income_fixtures()
    _check_existing_fields(city_directory)

    print("Income parser validation completed successfully.")
    print(f"Playable factions covered: {len(PLAYABLE_FACTIONS)}")
    for faction, sid, level, income in normalized_rows:
        values = ", ".join(
            f"{name}={value}"
            for name, value in income.as_dict().items()
            if value
        )
        print(f"  {faction}: {sid} level {level}: {values}")
    print("Exact level-specific baseline income progression was retained.")
    print("Non-income military, dwelling, wall, and utility buildings remained zero.")
    print("Resource vectors used canonical fields and zeroed unrelated resources.")
    print("Malformed authoritative income fixtures were rejected with CityParseError.")
    print("BuildingLevel rejected negative income without changing ResourceCost semantics.")
    print("Existing parsed fields and database integration remained compatible.")
    print("Repeated parser output was deterministic.")


def _assert_only_gold(cost: ResourceCost, expected_gold: int) -> None:
    for name in RESOURCE_NAMES:
        expected = expected_gold if name == "gold" else 0
        actual = getattr(cost, name)
        if actual != expected:
            raise RuntimeError(
                f"Unexpected normalized income field {name}: expected {expected}, got {actual}"
            )


def _check_model_default_and_validation() -> None:
    building = BuildingLevel(
        key=BuildingKey("test", "Build_Test", 1),
        category="test",
        name_key=None,
        scene_slot=None,
        cost=ResourceCost(),
    )
    if building.income != ResourceCost():
        raise RuntimeError("BuildingLevel income default was not zero")

    try:
        BuildingLevel(
            key=BuildingKey("test", "Build_Test", 1),
            category="test",
            name_key=None,
            scene_slot=None,
            cost=ResourceCost(),
            income=ResourceCost(gold=-1),
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("Negative BuildingLevel income was accepted")

    if ResourceCost(gold=-1).gold != -1:
        raise RuntimeError("Signed ResourceCost behavior was changed globally")


def _check_malformed_income_fixtures() -> None:
    cases = {
        "unknown_resource": [{"type": "sideRes", "parameters": ["unknown", 5]}],
        "invalid_amount": [{"type": "sideRes", "parameters": ["gold", "bad"]}],
        "negative_amount": [{"type": "sideRes", "parameters": ["gold", -5]}],
        "missing_parameters": [{"type": "sideRes"}],
    }
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        for name, bonuses in cases.items():
            path = root / f"{name}.json"
            _write_fixture(path, bonuses_per_level=[{"bonuses": bonuses}])
            _expect_parse_error(path, "Build_Test", 1)

        malformed_container = root / "malformed_container.json"
        _write_fixture(malformed_container, bonuses_per_level={"bonuses": []})
        _expect_parse_error(malformed_container, "Build_Test", 1)

        malformed_level = root / "malformed_level.json"
        _write_fixture(malformed_level, bonuses_per_level=[{"bonuses": "bad"}])
        _expect_parse_error(malformed_level, "Build_Test", 1)

        duplicate = root / "duplicate_resources.json"
        _write_fixture(
            duplicate,
            bonuses_per_level=[{
                "bonuses": [
                    {"type": "sideRes", "parameters": ["gold", 2]},
                    {"type": "sideRes", "parameters": ["gold", 3]},
                    {"type": "sideRes", "parameters": ["wood", 4]},
                ]
            }],
        )
        parsed = parse_city_file(duplicate).get("Build_Test", 1).income
        if parsed != ResourceCost(gold=5, wood=4):
            raise RuntimeError("Duplicate or multiple resource income was not normalized")


def _write_fixture(path: Path, *, bonuses_per_level: object) -> None:
    data = {
        "array": [{
            "id": "test_city",
            "fraction": "test",
            "economy": [{
                "sid": "Build_Test",
                "names": ["Test"],
                "parametersPerLevel": [{
                    "prevBuildings": [],
                    "nodePos": {"xPos": 1, "yPos": 2},
                    "costs": [{"name": "gold", "cost": 10}],
                }],
                "bonusesPerLevel": bonuses_per_level,
            }],
        }],
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def _expect_parse_error(path: Path, sid: str, level: int) -> None:
    try:
        parse_city_file(path)
    except CityParseError as exc:
        message = str(exc)
        if str(path) not in message or sid not in message or f"level {level}" not in message:
            raise RuntimeError(f"Income parse error lacked source context: {message}") from exc
    else:
        raise RuntimeError(f"Malformed income fixture was accepted: {path.name}")


def _check_existing_fields(city_directory: Path) -> None:
    city = parse_city_file(city_directory / "undead_city.json")
    building = city.get("Build_Main", 2)
    if building.cost != ResourceCost(gold=2500, wood=5, ore=5):
        raise RuntimeError("Existing building cost changed")
    if building.prerequisites != (BuildingKey("undead", "Build_Main", 1),):
        raise RuntimeError("Existing prerequisites changed")
    if building.constructed_on_start:
        raise RuntimeError("Existing constructed-on-start behavior changed")
    if (building.node_x, building.node_y) != (1, 1):
        raise RuntimeError("Existing node position changed")


if __name__ == "__main__":
    main()
