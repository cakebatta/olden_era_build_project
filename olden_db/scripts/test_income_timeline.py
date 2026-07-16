from __future__ import annotations

from dataclasses import FrozenInstanceError

from olden_db.income_timeline import calculate_income_timeline
from olden_db.models import BuildingKey, BuildingLevel, FactionCity, ResourceCost
from olden_db.planner import BuildPlan, BuildStep, GameDate


def main() -> None:
    city, keys = _fixture_city()
    city_snapshot = dict(city.buildings)

    empty_plan = _plan(city.faction, keys["hall_1"], (), GameDate(1, 1, 1))
    empty_plan_snapshot = empty_plan

    canonical = calculate_income_timeline(
        city,
        empty_plan,
        through_date=GameDate(1, 1, 3),
    )
    _expect_day(canonical, GameDate(1, 1, 1), ResourceCost(gold=500))
    if canonical.events[0].building != keys["hall_1"]:
        raise RuntimeError("Canonical starting income used the wrong building")

    explicit_empty = calculate_income_timeline(
        city,
        empty_plan,
        through_date=GameDate(1, 1, 3),
        starting_buildings=frozenset(),
    )
    if explicit_empty == canonical:
        raise RuntimeError("Explicitly empty starting state matched canonical state")
    if explicit_empty.events or not explicit_empty.total_income.is_zero():
        raise RuntimeError("Explicitly empty starting state restored canonical income")

    explicit_added_set = frozenset({keys["bank"]})
    explicit_added_snapshot = explicit_added_set
    explicit_added = calculate_income_timeline(
        city,
        empty_plan,
        through_date=GameDate(1, 1, 2),
        starting_buildings=explicit_added_set,
    )
    _expect_day(
        explicit_added,
        GameDate(1, 1, 1),
        ResourceCost(wood=2, ore=1),
    )

    construction_plan = _plan(
        city.faction,
        keys["hall_2"],
        (
            _step(1, GameDate(1, 1, 1), keys["bank"]),
            _step(2, GameDate(1, 2, 1), keys["hall_2"]),
            _step(3, GameDate(1, 2, 2), keys["utility"]),
        ),
        GameDate(1, 1, 1),
    )
    timeline = calculate_income_timeline(
        city,
        construction_plan,
        through_date=GameDate(1, 2, 3),
    )

    # Bank completes 111 and first produces 112.
    bank_events_111 = [
        event for event in _day(timeline, GameDate(1, 1, 1)).events
        if event.building == keys["bank"]
    ]
    if bank_events_111:
        raise RuntimeError("New income building produced on construction day")
    bank_events_112 = [
        event for event in _day(timeline, GameDate(1, 1, 2)).events
        if event.building == keys["bank"]
    ]
    if len(bank_events_112) != 1:
        raise RuntimeError("New income building did not activate next day")

    # Hall level 2 completes 121. Level 1 applies on 121, level 2 on 122.
    hall_121 = _event_for_sid(timeline, GameDate(1, 2, 1), "Build_Main")
    hall_122 = _event_for_sid(timeline, GameDate(1, 2, 2), "Build_Main")
    if hall_121.building != keys["hall_1"] or hall_121.amount.gold != 500:
        raise RuntimeError("Lower income level did not remain active on upgrade day")
    if hall_122.building != keys["hall_2"] or hall_122.amount.gold != 1000:
        raise RuntimeError("Income upgrade did not activate the following day")

    hall_events_122 = [
        event for event in _day(timeline, GameDate(1, 2, 2)).events
        if event.building.sid == "Build_Main"
    ]
    if len(hall_events_122) != 1:
        raise RuntimeError("Income levels stacked instead of replacing")

    expected_122 = ResourceCost(gold=1000, wood=2, ore=1)
    _expect_day(timeline, GameDate(1, 2, 2), expected_122)
    if any(event.building == keys["utility"] for event in timeline.events):
        raise RuntimeError("Zero-income building produced an event")

    if tuple(day.date for day in timeline.daily_income) != tuple(
        GameDate(1, 1, 1).add_days(offset)
        for offset in range(10)
    ):
        raise RuntimeError("Daily records were not complete and chronological")
    for day in timeline.daily_income:
        if tuple(event.building for event in day.events) != tuple(
            sorted(event.building for event in day.events)
        ):
            raise RuntimeError("Daily events were not canonically ordered")

    # Default horizon equals completion date.
    default_horizon = calculate_income_timeline(city, construction_plan)
    if default_horizon.through_date != construction_plan.completion_date:
        raise RuntimeError("Default horizon did not equal plan completion")

    later = calculate_income_timeline(
        city,
        empty_plan,
        through_date=GameDate(2, 1, 1),
    )
    if later.through_date != GameDate(2, 1, 1):
        raise RuntimeError("Explicit later horizon was not honored")
    _expect_day(later, GameDate(1, 1, 7), ResourceCost(gold=500))
    _expect_day(later, GameDate(1, 2, 1), ResourceCost(gold=500))
    _expect_day(later, GameDate(1, 4, 7), ResourceCost(gold=500))
    _expect_day(later, GameDate(2, 1, 1), ResourceCost(gold=500))

    expected_days = GameDate(2, 1, 1).day_index + 1
    if len(later.daily_income) != expected_days:
        raise RuntimeError("Week/month transition lost evaluated days")
    if later.total_income != ResourceCost(gold=500 * expected_days):
        raise RuntimeError("Income total across boundaries was incorrect")

    later_start_plan = _plan(
        city.faction,
        keys["hall_1"],
        (),
        GameDate(1, 1, 2),
    )
    try:
        calculate_income_timeline(
            city,
            later_start_plan,
            through_date=GameDate(1, 1, 1),
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("Earlier-than-start horizon was not rejected")

    _check_starting_validation(city, empty_plan)
    _check_plan_validation(city, keys)

    repeated = calculate_income_timeline(
        city,
        construction_plan,
        through_date=GameDate(1, 2, 3),
    )
    if repeated != timeline:
        raise RuntimeError("Repeated income calculation was not deterministic")

    try:
        timeline.events = ()
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise RuntimeError("IncomeTimeline was mutable")

    try:
        timeline.daily_income[0].events = ()
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise RuntimeError("DailyIncome was mutable")

    try:
        timeline.events[0].amount = ResourceCost()
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise RuntimeError("IncomeEvent was mutable")

    if city.buildings != city_snapshot:
        raise RuntimeError("Income calculation mutated city data")
    if empty_plan != empty_plan_snapshot:
        raise RuntimeError("Income calculation mutated the plan")
    if explicit_added_set != explicit_added_snapshot:
        raise RuntimeError("Income calculation mutated the starting set")

    print("Income timeline validation completed successfully.")
    print("Canonical starting income began on the plan starting date.")
    print("Explicit empty starting state remained distinct from canonical defaults.")
    print("Scenario-added income buildings produced on the starting date.")
    print("New income buildings activated on the following day.")
    print("Income upgrades replaced lower-level amounts after a one-day delay.")
    print("Independent income buildings combined deterministically.")
    print("Multi-resource income was preserved.")
    print("Zero-income buildings produced no events.")
    print("Income continued across week and month boundaries.")
    print("Repeated calculations were deterministic and inputs remained unchanged.")


def _check_starting_validation(city, plan) -> None:
    try:
        calculate_income_timeline(city, plan, starting_buildings=set())
    except TypeError:
        pass
    else:
        raise RuntimeError("Mutable starting collection was not rejected")

    try:
        calculate_income_timeline(
            city,
            plan,
            starting_buildings=frozenset({"not-a-key"}),
        )
    except TypeError:
        pass
    else:
        raise RuntimeError("Non-BuildingKey member was not rejected")

    unknown = BuildingKey(city.faction, "Build_Unknown", 1)
    try:
        calculate_income_timeline(
            city,
            plan,
            starting_buildings=frozenset({unknown}),
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("Unknown starting building was not rejected")

    cross = BuildingKey("other", "Build_Main", 1)
    try:
        calculate_income_timeline(
            city,
            plan,
            starting_buildings=frozenset({cross}),
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("Cross-faction starting building was not rejected")


def _check_plan_validation(city, keys) -> None:
    wrong_faction = _plan(
        "other",
        BuildingKey("other", "Build_Main", 1),
        (),
        GameDate(1, 1, 1),
    )
    try:
        calculate_income_timeline(city, wrong_faction)
    except ValueError:
        pass
    else:
        raise RuntimeError("City/plan faction mismatch was not rejected")

    unknown = BuildingKey(city.faction, "Build_Unknown", 1)
    malformed = _plan(
        city.faction,
        keys["hall_1"],
        (_step(1, GameDate(1, 1, 1), unknown),),
        GameDate(1, 1, 1),
    )
    try:
        calculate_income_timeline(city, malformed)
    except ValueError:
        pass
    else:
        raise RuntimeError("Plan building absent from city was not rejected")


def _day(timeline, date):
    for daily in timeline.daily_income:
        if daily.date == date:
            return daily
    raise RuntimeError(f"Missing daily record for {date}")


def _event_for_sid(timeline, date, sid):
    matches = [
        event for event in _day(timeline, date).events
        if event.building.sid == sid
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one event for {sid} on {date}, found {len(matches)}"
        )
    return matches[0]


def _expect_day(timeline, date, expected):
    actual = _day(timeline, date).total
    if actual != expected:
        raise RuntimeError(
            f"Unexpected income on {date}: expected {expected}, got {actual}"
        )


def _fixture_city():
    faction = "test"
    hall_1 = BuildingKey(faction, "Build_Main", 1)
    hall_2 = BuildingKey(faction, "Build_Main", 2)
    bank = BuildingKey(faction, "Build_Bank", 1)
    utility = BuildingKey(faction, "Build_Utility", 1)

    city = FactionCity(faction=faction, city_id="income_test")
    city.add_building(
        _building(
            hall_1,
            ResourceCost(gold=500),
            constructed_on_start=True,
        )
    )
    city.add_building(_building(hall_2, ResourceCost(gold=1000)))
    city.add_building(
        _building(
            bank,
            ResourceCost(wood=2, ore=1),
        )
    )
    city.add_building(_building(utility, ResourceCost()))
    return city, {
        "hall_1": hall_1,
        "hall_2": hall_2,
        "bank": bank,
        "utility": utility,
    }


def _building(key, income, *, constructed_on_start=False):
    return BuildingLevel(
        key=key,
        category="test",
        name_key=None,
        scene_slot=None,
        cost=ResourceCost(),
        constructed_on_start=constructed_on_start,
        income=income,
    )


def _step(number, date, building):
    return BuildStep(
        step_number=number,
        date=date,
        building=building,
        individual_cost=ResourceCost(),
        cumulative_cost=ResourceCost(),
    )


def _plan(faction, target, steps, starting_date):
    return BuildPlan(
        faction=faction,
        target=target,
        order_number=1,
        steps=tuple(steps),
        total_cost=ResourceCost(),
        starting_date=starting_date,
    )


if __name__ == "__main__":
    main()
