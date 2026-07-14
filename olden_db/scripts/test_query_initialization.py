from __future__ import annotations

from olden_db.database import load_default_game_data
from olden_db.query import PlanningQueryService


def main() -> None:
    first = PlanningQueryService.from_default_game_data()
    second = PlanningQueryService.from_default_game_data()

    if not isinstance(first, PlanningQueryService):
        raise RuntimeError("Default factory did not return PlanningQueryService")
    if hasattr(first, "data") or hasattr(second, "data"):
        raise RuntimeError("Factory-created service exposes public backend state")

    fixture_data = load_default_game_data()
    faction = sorted(fixture_data.cities.cities)[0]
    target = sorted(fixture_data.cities.city(faction).buildings)[0]

    first_building = first.get_building(target.faction, target.sid, target.level)
    second_building = second.get_building(target.faction, target.sid, target.level)
    if first_building != second_building:
        raise RuntimeError("Default services returned inconsistent query results")

    explicit = PlanningQueryService(fixture_data)
    if explicit.get_building(target.faction, target.sid, target.level) != first_building:
        raise RuntimeError("Explicit construction behavior changed")

    print("Default Query Layer initialization validation completed successfully.")
    print(f"Loaded factions: {fixture_data.faction_count}")
    print(f"Loaded units: {fixture_data.unit_count}")
    print("Factory-created services returned identical query results.")
    print("Explicit PlanningQueryService construction remains supported.")
    print("Public backend state access is not exposed through service.data.")


if __name__ == "__main__":
    main()
