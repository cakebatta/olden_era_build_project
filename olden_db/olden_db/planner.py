from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .graph import (
    DependencyGraph,
    all_topological_orders,
    is_valid_topological_order,
)
from .models import BuildingKey, FactionCity, ResourceCost


class PlannerError(ValueError):
    """Base exception for build-planning errors."""


class InvalidBuildOrderError(PlannerError):
    """Raised when a supplied build order violates the dependency graph."""


@dataclass(frozen=True, slots=True, order=True)
class GameDate:
    """A Heroes-style month/week/day date."""

    month: int
    week: int
    day: int

    def __post_init__(self) -> None:
        if self.month < 1:
            raise ValueError("month must be at least 1")
        if not 1 <= self.week <= 4:
            raise ValueError("week must be between 1 and 4")
        if not 1 <= self.day <= 7:
            raise ValueError("day must be between 1 and 7")

    @classmethod
    def from_day_index(cls, day_index: int) -> "GameDate":
        """Convert zero-based day index 0 to date 111."""
        if day_index < 0:
            raise ValueError("day_index cannot be negative")

        month = day_index // 28 + 1
        day_within_month = day_index % 28
        week = day_within_month // 7 + 1
        day = day_within_month % 7 + 1
        return cls(month=month, week=week, day=day)

    @property
    def code(self) -> int:
        return self.month * 100 + self.week * 10 + self.day

    @property
    def day_index(self) -> int:
        return (self.month - 1) * 28 + (self.week - 1) * 7 + (self.day - 1)

    def add_days(self, days: int) -> "GameDate":
        new_index = self.day_index + days
        if new_index < 0:
            raise ValueError("date offset precedes 111")
        return GameDate.from_day_index(new_index)

    def __str__(self) -> str:
        return str(self.code)


@dataclass(frozen=True, slots=True)
class BuildStep:
    """One dated construction action within a build plan."""

    step_number: int
    date: GameDate
    building: BuildingKey
    individual_cost: ResourceCost
    cumulative_cost: ResourceCost

    def __post_init__(self) -> None:
        if self.step_number < 1:
            raise ValueError("step_number must be at least 1")


@dataclass(frozen=True, slots=True)
class BuildPlan:
    """A complete dated plan for one valid topological order."""

    faction: str
    target: BuildingKey
    order_number: int
    steps: tuple[BuildStep, ...]
    total_cost: ResourceCost
    starting_date: GameDate

    def __post_init__(self) -> None:
        if not self.faction:
            raise ValueError("faction cannot be empty")
        if self.target.faction != self.faction:
            raise ValueError("target faction does not match plan faction")
        if self.order_number < 1:
            raise ValueError("order_number must be at least 1")

    @property
    def build_actions(self) -> int:
        return len(self.steps)

    @property
    def completion_date(self) -> GameDate:
        if not self.steps:
            return self.starting_date
        return self.steps[-1].date

    @property
    def order(self) -> tuple[BuildingKey, ...]:
        return tuple(step.building for step in self.steps)


def plan_build_order(
    city: FactionCity,
    graph: DependencyGraph,
    order: Iterable[BuildingKey],
    *,
    order_number: int = 1,
    starting_date: GameDate = GameDate(1, 1, 1),
) -> BuildPlan:
    """
    Convert one legal topological order into a dated, costed build plan.

    Assumptions:
    - one building action per day;
    - resources are immediately available;
    - starting buildings require neither an action nor resource cost.
    """
    normalized_order = tuple(order)

    if city.faction != graph.faction:
        raise PlannerError(
            f"City faction {city.faction!r} does not match graph faction "
            f"{graph.faction!r}"
        )

    if not is_valid_topological_order(graph, normalized_order):
        raise InvalidBuildOrderError(
            f"Order is not valid for target {graph.target}"
        )

    cumulative = ResourceCost()
    steps: list[BuildStep] = []

    for index, key in enumerate(normalized_order):
        try:
            building = city.buildings[key]
        except KeyError as exc:
            raise PlannerError(
                f"Graph node {key} is absent from the city"
            ) from exc

        cumulative = cumulative + building.cost
        steps.append(
            BuildStep(
                step_number=index + 1,
                date=starting_date.add_days(index),
                building=key,
                individual_cost=building.cost,
                cumulative_cost=cumulative,
            )
        )

    return BuildPlan(
        faction=city.faction,
        target=graph.target,
        order_number=order_number,
        steps=tuple(steps),
        total_cost=cumulative,
        starting_date=starting_date,
    )


def plan_all_orders(
    city: FactionCity,
    graph: DependencyGraph,
    *,
    starting_date: GameDate = GameDate(1, 1, 1),
    max_orders: int | None = None,
) -> tuple[BuildPlan, ...]:
    """Create a dated plan for every valid topological order."""
    orders = all_topological_orders(graph, max_orders=max_orders)
    return tuple(
        plan_build_order(
            city,
            graph,
            order,
            order_number=index,
            starting_date=starting_date,
        )
        for index, order in enumerate(orders, start=1)
    )


def validate_plan_set(plans: Iterable[BuildPlan]) -> None:
    """
    Check invariants shared by all plans for one target.

    All valid orders must share final cost, action count, and completion date.
    Their intermediate unlock dates may differ.
    """
    normalized = tuple(plans)
    if not normalized:
        raise PlannerError("plan set cannot be empty")

    first = normalized[0]
    seen_orders: set[tuple[BuildingKey, ...]] = set()

    for plan in normalized:
        if plan.faction != first.faction:
            raise PlannerError("plan set contains multiple factions")
        if plan.target != first.target:
            raise PlannerError("plan set contains multiple targets")
        if plan.starting_date != first.starting_date:
            raise PlannerError("plan set contains multiple starting dates")
        if plan.build_actions != first.build_actions:
            raise PlannerError("plan set has inconsistent action counts")
        if plan.total_cost != first.total_cost:
            raise PlannerError("plan set has inconsistent total costs")
        if plan.completion_date != first.completion_date:
            raise PlannerError("plan set has inconsistent completion dates")
        if plan.order in seen_orders:
            raise PlannerError("plan set contains duplicate build orders")

        seen_orders.add(plan.order)
