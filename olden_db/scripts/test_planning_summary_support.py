from __future__ import annotations

from dataclasses import FrozenInstanceError

from olden_db.localization import parse_localization_file
from olden_db.paths import require_english_cities_localization_file
from olden_db.planner import DailyConstructionCost, PlannerResult
from olden_db.query import PlanningQueryService, QueryError


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def representative_request(service: PlanningQueryService) -> tuple[str, str, int]:
    faction = service.list_factions()[0]
    sid = service.list_buildings(faction)[0]
    level = service.list_building_levels(faction, sid)[0]
    return faction, sid, level


def test_daily_schedule_is_deterministic_and_matches_plan() -> None:
    service = PlanningQueryService.from_default_game_data()
    faction, sid, level = representative_request(service)

    first = service.generate_planner_result(faction, sid, level)
    second = service.generate_planner_result(faction, sid, level)

    require(first == second, "Identical requests returned different PlannerResult values")
    require(
        first.daily_construction_schedule == second.daily_construction_schedule,
        "Daily construction schedule is not deterministic",
    )
    require(
        len(first.daily_construction_schedule) == len(first.plan.steps),
        "Schedule length does not match accepted plan",
    )

    expected = tuple(
        (step.date, step.building, step.individual_cost)
        for step in first.plan.steps
    )
    actual = tuple(
        (entry.date, entry.building, entry.cost)
        for entry in first.daily_construction_schedule
    )
    require(actual == expected, "Schedule is not an exact accepted-plan projection")

    if first.daily_construction_schedule:
        entry = first.daily_construction_schedule[0]
        try:
            entry.cost = entry.cost  # type: ignore[misc]
        except FrozenInstanceError:
            pass
        else:
            raise AssertionError("DailyConstructionCost is mutable")


def test_planner_result_constructor_remains_compatible() -> None:
    service = PlanningQueryService.from_default_game_data()
    faction, sid, level = representative_request(service)
    plan = service.generate_build_plan(faction, sid, level)

    result = PlannerResult(plan)
    require(result.plan == plan, "Historical PlannerResult(plan) construction changed")
    require(result.diagnostics == (), "Historical diagnostics default changed")
    require(
        tuple(item.building for item in result.daily_construction_schedule)
        == plan.order,
        "Compatible PlannerResult construction did not derive the schedule",
    )

    if result.daily_construction_schedule:
        require(
            isinstance(result.daily_construction_schedule[0], DailyConstructionCost),
            "Schedule contains the wrong contract type",
        )


def test_query_layer_localization_uses_canonical_identity() -> None:
    service = PlanningQueryService.from_default_game_data()
    faction, sid, level = representative_request(service)
    building = service.get_building(faction, sid, level)

    display_text = service.get_building_display_text(building.key)
    catalog = parse_localization_file(
        require_english_cities_localization_file(),
        language="english",
    )
    expected = catalog.resolve(
        building.name_key,
        fallback=building.name_key or building.key.sid,
    ) or (building.name_key or building.key.sid)

    require(display_text == expected, "Query Layer localization returned wrong text")
    require(bool(display_text), "Query Layer localization returned empty display text")


def test_existing_query_service_constructor_and_planner_behavior_remain_valid() -> None:
    configured = PlanningQueryService.from_default_game_data()
    legacy = PlanningQueryService(configured._data)
    faction, sid, level = representative_request(legacy)

    first_plan = legacy.generate_build_plan(faction, sid, level)
    second_plan = legacy.generate_build_plan(faction, sid, level)
    result = legacy.generate_planner_result(faction, sid, level)

    require(first_plan == second_plan, "Existing planner behavior is not deterministic")
    require(result.plan == first_plan, "PlannerResult plan changed legacy BuildPlan behavior")

    building = legacy.get_building(faction, sid, level)
    try:
        legacy.get_building_display_text(building.key)
    except QueryError:
        pass
    else:
        raise AssertionError("Unconfigured localization did not report a QueryError")


def main() -> None:
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} planning summary support checks")


if __name__ == "__main__":
    main()
