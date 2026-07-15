from __future__ import annotations

from dataclasses import dataclass

from .models import BuildingKey, FactionCity, UnitFamily
from .planner import BuildPlan, GameDate


@dataclass(frozen=True, slots=True, order=True)
class DwellingStock:
    """Available shared creature stock for one dwelling on one date."""

    date: GameDate
    dwelling: BuildingKey
    unit_family: UnitFamily
    available: int

    def __post_init__(self) -> None:
        if self.available < 0:
            raise ValueError("available stock cannot be negative")


@dataclass(frozen=True, slots=True)
class RecruitmentStock:
    """Immutable daily recruitment-stock progression for one faction."""

    faction: str
    starting_date: GameDate
    through_date: GameDate
    entries: tuple[DwellingStock, ...]

    def __post_init__(self) -> None:
        if not self.faction:
            raise ValueError("faction cannot be empty")
        if self.through_date.day_index < self.starting_date.day_index:
            raise ValueError("through_date cannot precede starting_date")

    def on_date(self, date: GameDate) -> tuple[DwellingStock, ...]:
        if not isinstance(date, GameDate):
            raise TypeError("date must be a GameDate")
        return tuple(entry for entry in self.entries if entry.date == date)

    def available(self, dwelling: BuildingKey, date: GameDate) -> int:
        for entry in self.entries:
            if entry.dwelling == dwelling and entry.date == date:
                return entry.available
        raise KeyError(f"No stock entry for dwelling={dwelling!r}, date={date}")


@dataclass(frozen=True, slots=True)
class _DwellingDefinition:
    key: BuildingKey
    family: UnitFamily
    building_keys: frozenset[BuildingKey]


def calculate_recruitment_stock(
    city: FactionCity,
    plan: BuildPlan,
    *,
    through_date: GameDate | None = None,
) -> RecruitmentStock:
    """Calculate deterministic daily creature availability without recruitment.

    Weekly additions occur before construction on the first day of each week.
    A dwelling or wall built that day therefore does not affect that day's
    weekly grant. Initial dwelling stock is added when the dwelling first
    becomes available and ignores wall modifiers.
    """
    if not isinstance(city, FactionCity):
        raise TypeError("city must be a FactionCity")
    if not isinstance(plan, BuildPlan):
        raise TypeError("plan must be a BuildPlan")
    if through_date is not None and not isinstance(through_date, GameDate):
        raise TypeError("through_date must be a GameDate or None")
    if city.faction != plan.faction:
        raise ValueError("city faction does not match plan faction")

    end_date = plan.completion_date if through_date is None else through_date
    if end_date.day_index < plan.starting_date.day_index:
        raise ValueError("through_date cannot precede plan starting date")

    definitions = _collect_dwellings(city)
    construction_by_date = _construction_by_date(city, plan)
    available_buildings = {
        key
        for key, building in city.buildings.items()
        if building.constructed_on_start
    }
    stock = {definition.key: 0 for definition in definitions}
    activated: set[BuildingKey] = set()

    for definition in definitions:
        if definition.building_keys & available_buildings:
            stock[definition.key] = definition.family.weekly_growth
            activated.add(definition.key)

    entries: list[DwellingStock] = []
    for day_index in range(plan.starting_date.day_index, end_date.day_index + 1):
        date = GameDate.from_day_index(day_index)

        if date.day == 1 and date != plan.starting_date:
            wall_level = _highest_available_wall_level(city, available_buildings)
            for definition in definitions:
                if definition.key in activated:
                    stock[definition.key] += _modified_weekly_growth(
                        definition.family.weekly_growth,
                        wall_level,
                    )

        for key in construction_by_date.get(date, ()):
            available_buildings.add(key)
            for definition in definitions:
                if definition.key not in activated and key in definition.building_keys:
                    stock[definition.key] += definition.family.weekly_growth
                    activated.add(definition.key)

        for definition in definitions:
            entries.append(
                DwellingStock(
                    date=date,
                    dwelling=definition.key,
                    unit_family=definition.family,
                    available=stock[definition.key],
                )
            )

    return RecruitmentStock(
        faction=city.faction,
        starting_date=plan.starting_date,
        through_date=end_date,
        entries=tuple(entries),
    )


def _collect_dwellings(city: FactionCity) -> tuple[_DwellingDefinition, ...]:
    grouped: dict[str, list[tuple[BuildingKey, UnitFamily]]] = {}
    for key, building in city.buildings.items():
        if building.unit_family is None:
            continue
        grouped.setdefault(building.unit_family.dwelling_sid, []).append(
            (key, building.unit_family)
        )

    definitions: list[_DwellingDefinition] = []
    for dwelling_sid, items in grouped.items():
        families = {family for _, family in items}
        if len(families) != 1:
            raise ValueError(
                f"Inconsistent UnitFamily data for dwelling {dwelling_sid!r}"
            )
        keys = frozenset(key for key, _ in items)
        definitions.append(
            _DwellingDefinition(
                key=min(keys),
                family=items[0][1],
                building_keys=keys,
            )
        )
    return tuple(sorted(definitions, key=lambda item: item.key))


def _construction_by_date(
    city: FactionCity,
    plan: BuildPlan,
) -> dict[GameDate, tuple[BuildingKey, ...]]:
    mutable: dict[GameDate, list[BuildingKey]] = {}
    for step in plan.steps:
        if step.building not in city.buildings:
            raise ValueError(f"Plan building is absent from city: {step.building}")
        mutable.setdefault(step.date, []).append(step.building)
    return {date: tuple(sorted(keys)) for date, keys in mutable.items()}


def _highest_available_wall_level(
    city: FactionCity,
    available_buildings: set[BuildingKey],
) -> int:
    levels = [
        key.level
        for key in available_buildings
        if key.sid == "Build_Wall"
        and key.faction == city.faction
        and key in city.buildings
    ]
    return max(levels, default=0)


def _modified_weekly_growth(base_growth: int, wall_level: int) -> int:
    if wall_level >= 3:
        return base_growth * 2
    if wall_level == 2:
        return base_growth * 3 // 2
    return base_growth
