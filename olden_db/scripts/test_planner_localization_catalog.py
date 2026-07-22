from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory

from olden_db.database import load_default_game_data
from olden_db.localization import DuplicateLocalizationKeyError, LocalizationCatalog, parse_localization_file, parse_localization_files
from olden_db.models import BuildingKey
from olden_db.paths import require_english_cities_localization_file
from olden_db.planner_localization import build_planner_localization_catalog
from olden_db.query import PlanningQueryService, UnknownUnitError


def _default_catalog():
    data = load_default_game_data()
    localization = parse_localization_file(require_english_cities_localization_file(), language="english")
    return data, build_planner_localization_catalog(data, localization)


def test_catalog_construction_and_repeated_lookup() -> None:
    data, catalog = _default_catalog()
    faction = sorted(data.cities.cities)[0]
    first = catalog.get_faction_display_name(faction)
    assert first
    assert first == catalog.get_faction_display_name(faction)


def test_building_lookup_and_fallback() -> None:
    data = load_default_game_data()
    building = next(iter(data.cities.city("human").buildings))
    catalog = build_planner_localization_catalog(data, LocalizationCatalog(language="test", tokens={}))
    assert catalog.get_building_display_name(building) == building.sid


def test_unit_and_upgrade_lookup() -> None:
    data, catalog = _default_catalog()
    unit = next(iter(sorted(data.units.units.values(), key=lambda item: item.sid)))
    assert catalog.get_unit_display_name(unit.faction, unit.sid)
    upgrades = [item for item in data.units.units.values() if "_upg" in item.sid or item.upgrade_sid is not None]
    if upgrades:
        item = sorted(upgrades, key=lambda value: value.sid)[0]
        assert catalog.get_upgrade_display_name(item.faction, item.sid)


def test_faction_localized_success() -> None:
    data = load_default_game_data()
    catalog = build_planner_localization_catalog(data, LocalizationCatalog(language="test", tokens={"human_name": "Localized Human"}))
    assert catalog.get_faction_display_name("human") == "Localized Human"


def test_planner_entity_filtering() -> None:
    data = load_default_game_data()
    catalog = build_planner_localization_catalog(data, LocalizationCatalog(language="test", tokens={"human_name": "Localized Human", "launcher_start_button": "Ignored"}))
    assert catalog.get_faction_display_name("human") == "Localized Human"
    assert not hasattr(catalog, "tokens")


def test_immutable_catalog_behavior() -> None:
    _, catalog = _default_catalog()
    try:
        catalog.language = "changed"
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise AssertionError("catalog allowed public mutation")
    try:
        catalog._faction_names["human"] = "changed"
    except TypeError:
        pass
    else:
        raise AssertionError("catalog mapping allowed mutation")


def test_duplicate_parser_behavior_unchanged() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        left = root / "left.json"
        right = root / "right.json"
        left.write_text('{"tokens":[{"sid":"same","text":"left"}]}', encoding="utf-8")
        right.write_text('{"tokens":[{"sid":"same","text":"right"}]}', encoding="utf-8")
        try:
            parse_localization_files((left, right), language="test")
        except DuplicateLocalizationKeyError:
            pass
        else:
            raise AssertionError("conflicting duplicate localization was accepted")


def test_query_layer_integration_and_compatibility() -> None:
    service = PlanningQueryService.from_default_game_data()
    faction = service.list_factions()[0]
    sid = service.list_buildings(faction)[0]
    level = service.list_building_levels(faction, sid)[0]
    key = BuildingKey(faction, sid, level)
    assert service.get_faction_display_name(faction)
    assert service.get_faction_display_text(faction)
    assert service.get_building_display_name(key)
    assert service.get_building_display_text(key)
    unit = service._data.units.faction_units(faction)[0]
    assert service.get_unit_display_name(faction, unit.sid)
    assert service.get_unit_display_text(unit.sid)
    assert service.get_unit_display_text(faction, unit.sid)
    try:
        service.get_unit_display_name(faction, "__missing_unit__")
    except UnknownUnitError:
        pass
    else:
        raise AssertionError("unknown unit did not raise UnknownUnitError")


def main() -> None:
    tests = [
        test_catalog_construction_and_repeated_lookup,
        test_building_lookup_and_fallback,
        test_unit_and_upgrade_lookup,
        test_faction_localized_success,
        test_planner_entity_filtering,
        test_immutable_catalog_behavior,
        test_duplicate_parser_behavior_unchanged,
        test_query_layer_integration_and_compatibility,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} planner localization checks")


if __name__ == "__main__":
    main()
