from __future__ import annotations

from dataclasses import FrozenInstanceError

from olden_db.income_timeline import (
    DailyIncome,
    IncomeEvent,
    IncomeTimeline,
    calculate_income_timeline,
)
from olden_db.models import (
    BuildingKey,
    BuildingLevel,
    FactionCity,
    ResourceCost,
    UnitFamily,
)
from olden_db.planner import BuildPlan, BuildStep, GameDate
from olden_db.recruitment_stock import calculate_recruitment_stock
from olden_db.resource_ledger import (
    RecruitmentAction,
    build_resource_ledger,
)


def main() -> None:
    city, plan, stock, timeline, actions = _fixture()
    city_snapshot = dict(city.buildings)
    plan_snapshot = plan
    stock_snapshot = stock
    timeline_snapshot = timeline

    ledger = build_resource_ledger(
        city,
        plan,
        stock,
        actions,
        ResourceCost(gold=50),
        starting_buildings=frozenset(
            {BuildingKey(city.faction, "Build_Main", 1)}
        ),
        income_timeline=timeline,
    )

    if ledger.income_timeline is not timeline:
        raise RuntimeError("ResourceLedger did not retain the source timeline")
    if ledger.income_total != timeline.total_income:
        raise RuntimeError("Income total did not match the certified timeline")
    if ledger.combined_total != (
        ledger.construction_total + ledger.recruitment_total
    ):
        raise RuntimeError("Existing spending-total semantics changed")

    # Day 111: +100 income, -150 construction, -20 recruitment.
    first_income = ledger.income_entries[0]
    first_construction = ledger.construction_entries[0]
    first_recruitment = ledger.recruitment_entries[0]
    if first_income.date != GameDate(1, 1, 1):
        raise RuntimeError("Starting-day income was not applied")
    if first_income.balance_after != ResourceCost(gold=150):
        raise RuntimeError("Income was not applied before same-day spending")
    if first_construction.balance_after != ResourceCost(gold=0):
        raise RuntimeError("Construction did not follow income")
    if first_recruitment.balance_after != ResourceCost(gold=-20):
        raise RuntimeError("Recruitment did not follow construction")

    if ledger.feasible:
        raise RuntimeError("Expected recruitment deficit was not reported")
    if ledger.first_deficit is None:
        raise RuntimeError("First deficit was not retained")
    if ledger.first_deficit.date != GameDate(1, 1, 1):
        raise RuntimeError("First deficit date was incorrect")
    if ledger.first_deficit.resource != "gold":
        raise RuntimeError("First deficit resource was incorrect")

    # The bank completed on 111. Its multi-resource income begins on 112
    # because that timing is already frozen in IncomeTimeline.
    day_112_income = [
        entry
        for entry in ledger.income_entries
        if entry.date == GameDate(1, 1, 2)
    ]
    if tuple(entry.building for entry in day_112_income) != tuple(
        sorted(entry.building for entry in day_112_income)
    ):
        raise RuntimeError("Income entries did not preserve canonical ordering")
    if sum(entry.amount.wood for entry in day_112_income) != 2:
        raise RuntimeError("Multi-resource income was not applied")
    if sum(entry.amount.ore for entry in day_112_income) != 1:
        raise RuntimeError("Multi-resource income was not applied")

    # Prove the ledger consumes the supplied timeline rather than reading
    # BuildingLevel.income or reconstructing activation.
    synthetic = _synthetic_timeline(
        city.faction,
        plan.starting_date,
        stock.through_date,
        BuildingKey(city.faction, "Build_Main", 1),
        ResourceCost(gold=77),
    )
    synthetic_ledger = build_resource_ledger(
        city,
        plan,
        stock,
        (),
        ResourceCost(),
        income_timeline=synthetic,
    )
    expected_synthetic = ResourceCost(
        gold=77 * len(synthetic.daily_income)
    )
    if synthetic_ledger.income_total != expected_synthetic:
        raise RuntimeError("Ledger reconstructed income instead of consuming it")

    repeated = build_resource_ledger(
        city,
        plan,
        stock,
        actions,
        ResourceCost(gold=50),
        starting_buildings=frozenset(
            {BuildingKey(city.faction, "Build_Main", 1)}
        ),
        income_timeline=timeline,
    )
    if repeated != ledger:
        raise RuntimeError("Income-aware ledger was not deterministic")

    _check_validation(city, plan, stock, timeline)
    _check_legacy_no_income_mode(city, plan, stock)

    try:
        ledger.income_entries = ()
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise RuntimeError("ResourceLedger income data was mutable")

    try:
        ledger.income_entries[0].amount = ResourceCost()
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise RuntimeError("IncomeLedgerEntry was mutable")

    if city.buildings != city_snapshot:
        raise RuntimeError("Ledger mutated the city")
    if plan != plan_snapshot:
        raise RuntimeError("Ledger mutated the plan")
    if stock != stock_snapshot:
        raise RuntimeError("Ledger mutated RecruitmentStock")
    if timeline != timeline_snapshot:
        raise RuntimeError("Ledger mutated IncomeTimeline")

    print("Income-aware resource ledger validation completed successfully.")
    print("Certified IncomeTimeline events were consumed without reconstruction.")
    print("Beginning-of-day income preceded construction and recruitment spending.")
    print("Income source entries and canonical event ordering were preserved.")
    print("Multi-resource income and total income were retained.")
    print("Daily balances and first-deficit reporting included income.")
    print("Construction and recruitment totals preserved existing semantics.")
    print("Timeline faction, start date, and horizon consistency were validated.")
    print("Legacy no-income calls remained backward compatible.")
    print("Repeated ledgers were deterministic and all source inputs remained unchanged.")


def _check_validation(city, plan, stock, timeline) -> None:
    wrong_faction = IncomeTimeline(
        faction="other",
        starting_date=timeline.starting_date,
        through_date=timeline.through_date,
        events=(),
        daily_income=tuple(
            DailyIncome(day.date, (), ResourceCost())
            for day in timeline.daily_income
        ),
        total_income=ResourceCost(),
    )
    _expect_value_error(
        lambda: build_resource_ledger(
            city,
            plan,
            stock,
            (),
            ResourceCost(),
            income_timeline=wrong_faction,
        ),
        "IncomeTimeline faction mismatch was accepted",
    )

    wrong_start = IncomeTimeline(
        faction=timeline.faction,
        starting_date=GameDate(1, 1, 2),
        through_date=GameDate(1, 1, 2),
        events=(),
        daily_income=(
            DailyIncome(GameDate(1, 1, 2), (), ResourceCost()),
        ),
        total_income=ResourceCost(),
    )
    _expect_value_error(
        lambda: build_resource_ledger(
            city,
            plan,
            stock,
            (),
            ResourceCost(),
            income_timeline=wrong_start,
        ),
        "IncomeTimeline starting-date mismatch was accepted",
    )

    short = IncomeTimeline(
        faction=timeline.faction,
        starting_date=timeline.starting_date,
        through_date=timeline.starting_date,
        events=(),
        daily_income=(
            DailyIncome(timeline.starting_date, (), ResourceCost()),
        ),
        total_income=ResourceCost(),
    )
    _expect_value_error(
        lambda: build_resource_ledger(
            city,
            plan,
            stock,
            (),
            ResourceCost(),
            income_timeline=short,
        ),
        "Incomplete IncomeTimeline horizon was accepted",
    )

    try:
        build_resource_ledger(
            city,
            plan,
            stock,
            (),
            ResourceCost(),
            income_timeline=object(),
        )
    except TypeError:
        pass
    else:
        raise RuntimeError("Malformed income timeline was accepted")


def _check_legacy_no_income_mode(city, plan, stock) -> None:
    ledger = build_resource_ledger(
        city,
        plan,
        stock,
        (),
        ResourceCost(gold=1000),
    )
    if ledger.income_timeline is not None:
        raise RuntimeError("Legacy ledger invented an IncomeTimeline")
    if ledger.income_entries or not ledger.income_total.is_zero():
        raise RuntimeError("Legacy ledger invented income")
    if ledger.ending_balance != (
        ledger.starting_resources - ledger.combined_total
    ):
        raise RuntimeError("Legacy no-income accounting changed")


def _fixture():
    faction = "test"
    hall = BuildingKey(faction, "Build_Main", 1)
    bank = BuildingKey(faction, "Build_Bank", 1)
    dwelling = BuildingKey(faction, "Build_Tier_1", 1)
    family = UnitFamily(
        faction=faction,
        tier=1,
        dwelling_sid=dwelling.sid,
        base_sid="Unit_Base",
        upgrade_option_1_sid="Unit_Upgrade_A",
        upgrade_option_2_sid="Unit_Upgrade_B",
        weekly_growth=5,
        base_cost=ResourceCost(gold=20),
        upgraded_cost=ResourceCost(gold=30),
    )

    city = FactionCity(faction=faction, city_id="income_ledger")
    city.add_building(
        BuildingLevel(
            key=hall,
            category="economy",
            name_key=None,
            scene_slot=None,
            cost=ResourceCost(),
            constructed_on_start=True,
            income=ResourceCost(gold=100),
        )
    )
    city.add_building(
        BuildingLevel(
            key=bank,
            category="economy",
            name_key=None,
            scene_slot=None,
            cost=ResourceCost(gold=150),
            income=ResourceCost(wood=2, ore=1),
        )
    )
    city.add_building(
        BuildingLevel(
            key=dwelling,
            category="hires",
            name_key=None,
            scene_slot=None,
            cost=ResourceCost(),
            constructed_on_start=True,
            unit_family=family,
        )
    )

    plan = BuildPlan(
        faction=faction,
        target=bank,
        order_number=1,
        steps=(
            BuildStep(
                step_number=1,
                date=GameDate(1, 1, 1),
                building=bank,
                individual_cost=ResourceCost(gold=150),
                cumulative_cost=ResourceCost(gold=150),
            ),
        ),
        total_cost=ResourceCost(gold=150),
        starting_date=GameDate(1, 1, 1),
    )
    effective = frozenset({hall, dwelling})
    through = GameDate(1, 1, 3)
    stock = calculate_recruitment_stock(
        city,
        plan,
        through_date=through,
        starting_buildings=effective,
    )
    timeline = calculate_income_timeline(
        city,
        plan,
        through_date=through,
        starting_buildings=effective,
    )
    actions = (
        RecruitmentAction(
            date=GameDate(1, 1, 1),
            dwelling=dwelling,
            base_quantity=1,
        ),
    )
    return city, plan, stock, timeline, actions


def _synthetic_timeline(
    faction,
    starting_date,
    through_date,
    building,
    amount,
):
    daily = []
    events = []
    total = ResourceCost()
    day_count = through_date.day_index - starting_date.day_index + 1
    for offset in range(day_count):
        date = starting_date.add_days(offset)
        event = IncomeEvent(date=date, building=building, amount=amount)
        events.append(event)
        daily.append(DailyIncome(date, (event,), amount))
        total = total + amount
    return IncomeTimeline(
        faction=faction,
        starting_date=starting_date,
        through_date=through_date,
        events=tuple(events),
        daily_income=tuple(daily),
        total_income=total,
    )


def _expect_value_error(callback, message):
    try:
        callback()
    except ValueError:
        return
    raise RuntimeError(message)


if __name__ == "__main__":
    main()
