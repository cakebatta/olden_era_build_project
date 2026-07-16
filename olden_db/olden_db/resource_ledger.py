from __future__ import annotations

from dataclasses import dataclass, field

from .constants import RESOURCE_NAMES
from .income_timeline import IncomeTimeline
from .models import BuildingKey, FactionCity, ResourceCost, UnitFamily
from .planner import BuildPlan, GameDate
from .recruitment_stock import RecruitmentStock


@dataclass(frozen=True, slots=True)
class RecruitmentAction:
    """One dated direct-recruitment request from shared dwelling stock."""

    date: GameDate
    dwelling: BuildingKey
    base_quantity: int = 0
    upgraded_quantity: int = 0

    def __post_init__(self) -> None:
        if self.base_quantity < 0 or self.upgraded_quantity < 0:
            raise ValueError("recruitment quantities cannot be negative")
        if self.base_quantity + self.upgraded_quantity < 1:
            raise ValueError("recruitment action must recruit at least one creature")


@dataclass(frozen=True, slots=True)
class IncomeLedgerEntry:
    """One certified IncomeTimeline event applied to the resource balance."""

    date: GameDate
    building: BuildingKey
    amount: ResourceCost
    balance_after: ResourceCost


@dataclass(frozen=True, slots=True)
class ConstructionLedgerEntry:
    date: GameDate
    building: BuildingKey
    cost: ResourceCost
    balance_after: ResourceCost


@dataclass(frozen=True, slots=True)
class RecruitmentLedgerEntry:
    date: GameDate
    action: RecruitmentAction
    unit_family: UnitFamily
    cost: ResourceCost
    stock_before: int
    stock_after: int
    balance_after: ResourceCost


@dataclass(frozen=True, slots=True)
class DailyResourceBalance:
    """End-of-day resource balance after income and all dated expenses."""

    date: GameDate
    balance: ResourceCost


@dataclass(frozen=True, slots=True)
class ResourceDeficit:
    date: GameDate
    resource: str
    balance: int
    entry_index: int

    def __post_init__(self) -> None:
        if self.resource not in RESOURCE_NAMES:
            raise ValueError(f"Unknown resource name: {self.resource!r}")
        if self.balance >= 0:
            raise ValueError("deficit balance must be negative")
        if self.entry_index < 1:
            raise ValueError("entry_index must be at least 1")


@dataclass(frozen=True, slots=True)
class ResourceLedger:
    plan: BuildPlan
    stock: RecruitmentStock
    actions: tuple[RecruitmentAction, ...]
    starting_resources: ResourceCost
    construction_entries: tuple[ConstructionLedgerEntry, ...]
    recruitment_entries: tuple[RecruitmentLedgerEntry, ...]
    daily_balances: tuple[DailyResourceBalance, ...]
    construction_total: ResourceCost
    recruitment_total: ResourceCost
    combined_total: ResourceCost
    ending_balance: ResourceCost
    feasible: bool
    first_deficit: ResourceDeficit | None
    income_timeline: IncomeTimeline | None = None
    income_entries: tuple[IncomeLedgerEntry, ...] = ()
    income_total: ResourceCost = field(default_factory=ResourceCost)


def build_resource_ledger(
    city: FactionCity,
    plan: BuildPlan,
    stock: RecruitmentStock,
    recruitment_actions: tuple[RecruitmentAction, ...],
    starting_resources: ResourceCost,
    *,
    starting_buildings: frozenset[BuildingKey] | None = None,
    income_timeline: IncomeTimeline | None = None,
) -> ResourceLedger:
    """Build a deterministic income, construction, and recruitment ledger.

    The canonical daily accounting order is:

    1. apply supplied ``IncomeTimeline`` events;
    2. complete construction and apply its cost;
    3. apply recruitment costs;
    4. record the end-of-day balance.

    Income timing, activation, and upgrade replacement are not calculated here.
    The ledger consumes the supplied immutable ``IncomeTimeline`` exactly.

    ``starting_buildings=None`` derives canonical starting buildings from
    ``city``. An explicitly supplied frozenset is authoritative, including an
    empty set. The starting set is used only for recruitment upgrade unlocks.

    ``income_timeline=None`` is retained as a backward-compatible no-income
    mode for callers awaiting Income Timeline orchestration.
    """
    if not isinstance(city, FactionCity):
        raise TypeError("city must be a FactionCity")
    if not isinstance(plan, BuildPlan):
        raise TypeError("plan must be a BuildPlan")
    if not isinstance(stock, RecruitmentStock):
        raise TypeError("stock must be a RecruitmentStock")
    if income_timeline is not None and not isinstance(
        income_timeline,
        IncomeTimeline,
    ):
        raise TypeError("income_timeline must be an IncomeTimeline or None")
    if not isinstance(recruitment_actions, tuple):
        raise TypeError("recruitment_actions must be a tuple")
    if not isinstance(starting_resources, ResourceCost):
        raise TypeError("starting_resources must be a ResourceCost")
    if starting_buildings is not None and not isinstance(
        starting_buildings,
        frozenset,
    ):
        raise TypeError("starting_buildings must be a frozenset or None")

    if city.faction != plan.faction or city.faction != stock.faction:
        raise ValueError("city, plan, and recruitment stock factions must match")
    if stock.starting_date != plan.starting_date:
        raise ValueError("recruitment stock starting date must match plan")

    if income_timeline is not None:
        if income_timeline.faction != plan.faction:
            raise ValueError(
                "income timeline faction must match city, plan, and stock"
            )
        if income_timeline.starting_date != plan.starting_date:
            raise ValueError("income timeline starting date must match plan")

    for step in plan.steps:
        if step.building not in city.buildings:
            raise ValueError(f"Plan building is absent from city: {step.building}")

    effective_starting = _resolve_starting_buildings(city, starting_buildings)

    if any(getattr(starting_resources, name) < 0 for name in RESOURCE_NAMES):
        raise ValueError("starting resources cannot contain negative values")
    if any(
        not isinstance(action, RecruitmentAction)
        for action in recruitment_actions
    ):
        raise TypeError(
            "recruitment_actions must contain RecruitmentAction values"
        )

    indexed_actions = tuple(enumerate(recruitment_actions))
    seen: set[tuple[GameDate, BuildingKey]] = set()
    for _, action in indexed_actions:
        key = (action.date, action.dwelling)
        if key in seen:
            raise ValueError(
                "duplicate recruitment action for the same dwelling and date"
            )
        seen.add(key)
        if action.dwelling.faction != plan.faction:
            raise ValueError("recruitment action faction does not match plan")
        if action.date.day_index < plan.starting_date.day_index:
            raise ValueError("recruitment action precedes plan starting date")
        if action.date.day_index > stock.through_date.day_index:
            raise ValueError(
                "recruitment action exceeds recruitment-stock coverage"
            )

    ordered_actions = tuple(
        action
        for _, action in sorted(
            indexed_actions,
            key=lambda item: (item[1].date.day_index, item[0]),
        )
    )

    required_end_index = max(
        [plan.completion_date.day_index, stock.through_date.day_index]
        + [action.date.day_index for action in ordered_actions]
    )
    if (
        income_timeline is not None
        and income_timeline.through_date.day_index < required_end_index
    ):
        raise ValueError(
            "income timeline does not cover the complete ledger horizon"
        )

    end_index = max(
        required_end_index,
        (
            income_timeline.through_date.day_index
            if income_timeline is not None
            else required_end_index
        ),
    )

    construction_events = {step.date: step for step in plan.steps}
    actions_by_date: dict[GameDate, list[RecruitmentAction]] = {}
    for action in ordered_actions:
        actions_by_date.setdefault(action.date, []).append(action)

    income_by_date = (
        {daily.date: daily for daily in income_timeline.daily_income}
        if income_timeline is not None
        else {}
    )

    balance = starting_resources
    income_total = ResourceCost()
    construction_total = ResourceCost()
    recruitment_total = ResourceCost()
    income_entries: list[IncomeLedgerEntry] = []
    construction_entries: list[ConstructionLedgerEntry] = []
    recruitment_entries: list[RecruitmentLedgerEntry] = []
    daily_balances: list[DailyResourceBalance] = []
    purchased: dict[BuildingKey, int] = {}
    unlocked_level_2 = _initial_level_2_unlocks(effective_starting)
    first_deficit: ResourceDeficit | None = None
    event_index = 0

    for day_index in range(plan.starting_date.day_index, end_index + 1):
        date = GameDate.from_day_index(day_index)

        daily_income = income_by_date.get(date)
        if daily_income is not None:
            for event in daily_income.events:
                event_index += 1
                balance = balance + event.amount
                income_total = income_total + event.amount
                income_entries.append(
                    IncomeLedgerEntry(
                        date=event.date,
                        building=event.building,
                        amount=event.amount,
                        balance_after=balance,
                    )
                )

        step = construction_events.get(date)
        if step is not None:
            event_index += 1
            balance = balance - step.individual_cost
            construction_total = construction_total + step.individual_cost
            construction_entries.append(
                ConstructionLedgerEntry(
                    date=date,
                    building=step.building,
                    cost=step.individual_cost,
                    balance_after=balance,
                )
            )
            if step.building.level >= 2:
                unlocked_level_2.add(
                    (step.building.faction, step.building.sid)
                )
            if first_deficit is None:
                first_deficit = _deficit_for(balance, date, event_index)

        for action in actions_by_date.get(date, ()):
            family = _family_for(stock, action.dwelling, date)
            if action.upgraded_quantity > 0 and (
                action.dwelling.faction,
                action.dwelling.sid,
            ) not in unlocked_level_2:
                raise ValueError(
                    "Upgraded recruitment requires dwelling level 2: "
                    f"{action.dwelling}"
                )

            baseline = stock.available(action.dwelling, date)
            already_purchased = purchased.get(action.dwelling, 0)
            stock_before = baseline - already_purchased
            requested = action.base_quantity + action.upgraded_quantity
            if requested > stock_before:
                raise ValueError(
                    f"Recruitment exceeds available stock for "
                    f"{action.dwelling} on {date}: requested {requested}, "
                    f"available {stock_before}"
                )

            cost = _scale(
                family.base_cost,
                action.base_quantity,
            ) + _scale(
                family.upgraded_cost,
                action.upgraded_quantity,
            )
            purchased[action.dwelling] = already_purchased + requested
            balance = balance - cost
            recruitment_total = recruitment_total + cost
            event_index += 1
            recruitment_entries.append(
                RecruitmentLedgerEntry(
                    date=date,
                    action=action,
                    unit_family=family,
                    cost=cost,
                    stock_before=stock_before,
                    stock_after=stock_before - requested,
                    balance_after=balance,
                )
            )
            if first_deficit is None:
                first_deficit = _deficit_for(balance, date, event_index)

        daily_balances.append(
            DailyResourceBalance(date=date, balance=balance)
        )

    if income_timeline is not None and income_total != income_timeline.total_income:
        raise ValueError(
            "applied income does not match IncomeTimeline.total_income"
        )

    combined_total = construction_total + recruitment_total
    return ResourceLedger(
        plan=plan,
        stock=stock,
        actions=ordered_actions,
        starting_resources=starting_resources,
        construction_entries=tuple(construction_entries),
        recruitment_entries=tuple(recruitment_entries),
        daily_balances=tuple(daily_balances),
        construction_total=construction_total,
        recruitment_total=recruitment_total,
        combined_total=combined_total,
        ending_balance=balance,
        feasible=first_deficit is None,
        first_deficit=first_deficit,
        income_timeline=income_timeline,
        income_entries=tuple(income_entries),
        income_total=income_total,
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
            raise TypeError(
                "starting_buildings must contain BuildingKey values"
            )
        if key.faction != city.faction:
            raise ValueError(
                f"Starting building faction {key.faction!r} does not match "
                f"city faction {city.faction!r}: {key}"
            )
        if key not in city.buildings:
            raise ValueError(f"Unknown starting building: {key}")
    return starting_buildings


def _initial_level_2_unlocks(
    effective_starting: frozenset[BuildingKey],
) -> set[tuple[str, str]]:
    return {
        (key.faction, key.sid)
        for key in effective_starting
        if key.level >= 2
    }


def _family_for(
    stock: RecruitmentStock,
    dwelling: BuildingKey,
    date: GameDate,
) -> UnitFamily:
    for entry in stock.on_date(date):
        if entry.dwelling == dwelling:
            return entry.unit_family
    raise ValueError(f"Unknown dwelling in recruitment stock: {dwelling}")


def _scale(cost: ResourceCost, quantity: int) -> ResourceCost:
    return ResourceCost(
        **{
            name: getattr(cost, name) * quantity
            for name in RESOURCE_NAMES
        }
    )


def _deficit_for(
    balance: ResourceCost,
    date: GameDate,
    entry_index: int,
) -> ResourceDeficit | None:
    for resource in RESOURCE_NAMES:
        value = getattr(balance, resource)
        if value < 0:
            return ResourceDeficit(date, resource, value, entry_index)
    return None
