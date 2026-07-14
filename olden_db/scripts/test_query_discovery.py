from __future__ import annotations

from olden_db.query import (
    PlanningQueryService,
    UnknownBuildingError,
    UnknownFactionError,
)


def main() -> None:
    service = PlanningQueryService.from_default_game_data()

    first_factions = service.list_factions()
    second_factions = service.list_factions()
    if not first_factions:
        raise RuntimeError("Faction discovery returned no factions")
    if first_factions != second_factions:
        raise RuntimeError("Faction discovery was not deterministic")
    if first_factions != tuple(sorted(first_factions)):
        raise RuntimeError("Factions were not returned in sorted order")
    if len(first_factions) != len(set(first_factions)):
        raise RuntimeError("Faction discovery returned duplicate identifiers")

    faction = first_factions[0]
    first_buildings = service.list_buildings(faction)
    second_buildings = service.list_buildings(faction)
    if not first_buildings:
        raise RuntimeError("Building discovery returned no building SIDs")
    if first_buildings != second_buildings:
        raise RuntimeError("Building discovery was not deterministic")
    if first_buildings != tuple(sorted(first_buildings)):
        raise RuntimeError("Building SIDs were not returned in sorted order")
    if len(first_buildings) != len(set(first_buildings)):
        raise RuntimeError("Building discovery returned duplicate SIDs")

    sid = first_buildings[0]
    first_levels = service.list_building_levels(faction, sid)
    second_levels = service.list_building_levels(faction, sid)
    if not first_levels:
        raise RuntimeError("Level discovery returned no levels")
    if first_levels != second_levels:
        raise RuntimeError("Level discovery was not deterministic")
    if first_levels != tuple(sorted(first_levels)):
        raise RuntimeError("Building levels were not returned in sorted order")
    if len(first_levels) != len(set(first_levels)):
        raise RuntimeError("Level discovery returned duplicate levels")

    for level in first_levels:
        building = service.get_building(faction, sid, level)
        if building.key.faction != faction or building.key.sid != sid or building.key.level != level:
            raise RuntimeError("Discovered identifier did not resolve correctly")

    _check_invalid_faction(service)
    _check_invalid_sid(service, faction)

    print("Query Layer discovery validation completed successfully.")
    print(f"Factions discovered: {len(first_factions)}")
    print(f"Building SIDs discovered for {faction}: {len(first_buildings)}")
    print(f"Levels discovered for {faction}/{sid}: {first_levels}")
    print("Discovery results are deterministic and use canonical identifiers.")


def _check_invalid_faction(service: PlanningQueryService) -> None:
    try:
        service.list_buildings("not_a_faction")
    except UnknownFactionError:
        pass
    else:
        raise RuntimeError("Invalid faction did not raise UnknownFactionError")

    try:
        service.list_building_levels("not_a_faction", "missing")
    except UnknownFactionError:
        pass
    else:
        raise RuntimeError("Invalid faction level discovery did not raise UnknownFactionError")


def _check_invalid_sid(service: PlanningQueryService, faction: str) -> None:
    try:
        service.list_building_levels(faction, "not_a_building")
    except UnknownBuildingError:
        pass
    else:
        raise RuntimeError("Invalid SID did not raise UnknownBuildingError")


if __name__ == "__main__":
    main()
