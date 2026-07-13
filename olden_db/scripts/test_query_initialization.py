from __future__ import annotations

from olden_db.query import PlanningQueryService


def main() -> None:
    first = PlanningQueryService.from_default_game_data()
    second = PlanningQueryService.from_default_game_data()
    if not isinstance(first, PlanningQueryService):
        raise RuntimeError("Default factory did not return PlanningQueryService")
    if first.data.faction_count != second.data.faction_count:
        raise RuntimeError("Default services loaded inconsistent faction counts")
    if first.data.unit_count != second.data.unit_count:
        raise RuntimeError("Default services loaded inconsistent unit counts")
    faction = sorted(first.data.cities.cities)[0]
    target = sorted(first.data.cities.city(faction).buildings)[0]
    first_building = first.get_building(target.faction, target.sid, target.level)
    second_building = second.get_building(target.faction, target.sid, target.level)
    if first_building != second_building:
        raise RuntimeError("Default services returned inconsistent query results")
    explicit = PlanningQueryService(first.data)
    if explicit.get_building(target.faction, target.sid, target.level) != first_building:
        raise RuntimeError("Explicit construction behavior changed")
    print("Default Query Layer initialization validation completed successfully.")
    print(f"Loaded factions: {first.data.faction_count}")
    print(f"Loaded units: {first.data.unit_count}")
    print("Factory-created services returned identical query results.")
    print("Explicit PlanningQueryService construction remains supported.")


if __name__ == "__main__":
    main()
