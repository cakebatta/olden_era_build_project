from __future__ import annotations

from dataclasses import dataclass

from .models import BuildingKey, FactionCity, ResourceCost
from .planner import BuildPlan, GameDate


@dataclass(frozen=True, slots=True)
class IncomeEvent:
    """One nonzero income amount produced by one active building level."""

    date: GameDate
    building: BuildingKey
    amount: ResourceCost

    def __post_init__(self) -> None:
        if self.amount.is_zero():
            raise ValueError("income event amount cannot be zero")
        if any(value < 0 for value in self.amount.as_dict().values()):
            raise ValueError("income event amount cannot be negative")


@dataclass(frozen=True, slots=True)
class DailyIncome:
    """All deterministic town-building income produced on one date."""

    date: GameDate
    events: tuple[IncomeEvent, ...]
    total: ResourceCost

    def __post_init__(self) -> None:
        if any(event.date != self.date for event in self.events):
            raise ValueError("daily income contains an event for another date")
        if tuple(sorted(self.events, key=lambda event: event.building)) != self.events:
            raise ValueError("daily income events must use canonical building order")

        expected = ResourceCost()
        for event in self.events:
            expected = expected + event.amount
        if self.total != expected:
            raise ValueError("daily income total does not match its events")


@dataclass(frozen=True, slots=True)
class IncomeTimeline:
    """Immutable town-building income events over an inclusive date interval."""

    faction: str
    starting_date: GameDate
    through_date: GameDate
    events: tuple[IncomeEvent, ...]
    daily_income: tuple[DailyIncome, ...]
    total_income: ResourceCost

    def __post_init__(self) -> None:
        if not self.faction:
            raise ValueError("faction cannot be empty")
        if self.through_date.day_index < self.starting_date.day_index:
            raise ValueError("through_date cannot precede starting_date")

        expected_dates = tuple(
            self.starting_date.add_days(offset)
            for offset in range(
                self.through_date.day_index - self.starting_date.day_index + 1
            )
        )
        if tuple(day.date for day in self.daily_income) != expected_dates:
            raise ValueError(
                "daily_income must include every evaluated date in chronological order"
            )

        flattened = tuple(
            event
            for day in self.daily_income
            for event in day.events
        )
        if self.events != flattened:
            raise ValueError("flat events do not match daily income events")

        expected_total = ResourceCost()
        for day in self.daily_income:
            expected_total = expected_total + day.total
        if self.total_income != expected_total:
            raise ValueError("timeline total does not match daily totals")


def calculate_income_timeline(
    city: FactionCity,
    plan: BuildPlan,
    *,
    through_date: GameDate | None = None,
    starting_buildings: frozenset[BuildingKey] | None = None,
) -> IncomeTimeline:
    """Calculate deterministic town-building income without changing balances.

    ``starting_buildings=None`` derives canonical ``constructed_on_start``
    values. An explicitly supplied frozenset is authoritative, including an
    empty set.

    Starting buildings are active on ``plan.starting_date``. A building
    completed on date D becomes active on D + 1. For each building SID, only
    the highest active level determines income; levels never stack.
    """
    if not isinstance(city, FactionCity):
        raise TypeError("city must be a FactionCity")
    if not isinstance(plan, BuildPlan):
        raise TypeError("plan must be a BuildPlan")
    if through_date is not None and not isinstance(through_date, GameDate):
        raise TypeError("through_date must be a GameDate or None")
    if starting_buildings is not None and not isinstance(
        starting_buildings,
        frozenset,
    ):
        raise TypeError("starting_buildings must be a frozenset or None")
    if city.faction != plan.faction:
        raise ValueError("city faction does not match plan faction")

    end_date = plan.completion_date if through_date is None else through_date
    if end_date.day_index < plan.starting_date.day_index:
        raise ValueError("through_date cannot precede plan starting date")

    effective_starting = _resolve_starting_buildings(city, starting_buildings)
    activations = _construction_activations(city, plan)

    active_by_sid: dict[str, BuildingKey] = {}
    for key in sorted(effective_starting):
        _activate(active_by_sid, key)

    all_events: list[IncomeEvent] = []
    daily_records: list[DailyIncome] = []
    total_income = ResourceCost()

    day_count = end_date.day_index - plan.starting_date.day_index + 1
    for offset in range(day_count):
        date = plan.starting_date.add_days(offset)

        for key in activations.get(date, ()):
            _activate(active_by_sid, key)

        events: list[IncomeEvent] = []
        daily_total = ResourceCost()
        for key in sorted(active_by_sid.values()):
            amount = city.buildings[key].income
            if amount.is_zero():
                continue
            event = IncomeEvent(date=date, building=key, amount=amount)
            events.append(event)
            daily_total = daily_total + amount

        daily = DailyIncome(
            date=date,
            events=tuple(events),
            total=daily_total,
        )
        daily_records.append(daily)
        all_events.extend(events)
        total_income = total_income + daily_total

    return IncomeTimeline(
        faction=city.faction,
        starting_date=plan.starting_date,
        through_date=end_date,
        events=tuple(all_events),
        daily_income=tuple(daily_records),
        total_income=total_income,
    )


def _resolve_starting_buildings(
    city: FactionCity,
    starting_buildings: frozenset[BuildingKey] | None,
) -> frozenset[BuildingKey]:
    if starting_buildings is None:
        return frozenset(
            key
            for key, building in city.buildings.items()
            if building.constructed_on_start
        )

    for key in starting_buildings:
        if not isinstance(key, BuildingKey):
            raise TypeError("starting_buildings must contain BuildingKey values")
        if key.faction != city.faction:
            raise ValueError(
                f"Starting building faction {key.faction!r} does not match "
                f"city faction {city.faction!r}: {key}"
            )
        if key not in city.buildings:
            raise ValueError(f"Unknown starting building: {key}")

    return starting_buildings


def _construction_activations(
    city: FactionCity,
    plan: BuildPlan,
) -> dict[GameDate, tuple[BuildingKey, ...]]:
    mutable: dict[GameDate, list[BuildingKey]] = {}
    for step in plan.steps:
        if step.building not in city.buildings:
            raise ValueError(f"Plan building is absent from city: {step.building}")
        activation_date = step.date.add_days(1)
        mutable.setdefault(activation_date, []).append(step.building)

    return {
        date: tuple(sorted(keys))
        for date, keys in mutable.items()
    }


def _activate(
    active_by_sid: dict[str, BuildingKey],
    key: BuildingKey,
) -> None:
    current = active_by_sid.get(key.sid)
    if current is None or key.level > current.level:
        active_by_sid[key.sid] = key
