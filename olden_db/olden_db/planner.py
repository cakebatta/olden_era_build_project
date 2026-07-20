from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .graph import (
    DependencyGraph,
    all_topological_orders,
    is_valid_topological_order,
)
from .models import BuildingKey, FactionCity, ResourceCost
from .planner_diagnostics import (
    PlannerDiagnostic,
    PlannerDiagnosticCategory,
)


class PlannerError(ValueError):
    """Base exception for build-planning errors."""


class PlanningFailure(PlannerError):
    """Authoritative planning failure carrying canonical structured diagnostics."""

    def __init__(
        self,
        message: str,
        *,
        diagnostics: tuple[PlannerDiagnostic, ...],
    ) -> None:
        super().__init__(message)
        normalized = tuple(diagnostics)
        if not normalized:
            raise ValueError("planning failures require at least one diagnostic")
        if any(not isinstance(item, PlannerDiagnostic) for item in normalized):
            raise TypeError("diagnostics must contain PlannerDiagnostic values")
        self.diagnostics = normalized


class InvalidBuildOrderError(PlanningFailure):
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


@dataclass(frozen=True, slots=True)
class DailyConstructionCost:
    """Immutable construction-cost projection for one dated plan action."""

    date: GameDate
    building: BuildingKey
    cost: ResourceCost

    def __post_init__(self) -> None:
        if not isinstance(self.date, GameDate):
            raise TypeError("date must be a GameDate")
        if not isinstance(self.building, BuildingKey):
            raise TypeError("building must be a BuildingKey")
        if not isinstance(self.cost, ResourceCost):
            raise TypeError("cost must be a ResourceCost")


@dataclass(frozen=True, slots=True)
class PlannerResult:
    """Successful planner result with canonical structured diagnostics."""

    plan: BuildPlan
    diagnostics: tuple[PlannerDiagnostic, ...] = ()
    daily_construction_schedule: tuple[DailyConstructionCost, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.plan, BuildPlan):
            raise TypeError("plan must be a BuildPlan")
        normalized = tuple(self.diagnostics)
        if any(not isinstance(item, PlannerDiagnostic) for item in normalized):
            raise TypeError("diagnostics must contain PlannerDiagnostic values")
        object.__setattr__(self, "diagnostics", normalized)

        schedule = tuple(self.daily_construction_schedule)
        if not schedule:
            schedule = tuple(
                DailyConstructionCost(
                    date=step.date,
                    building=step.building,
                    cost=step.individual_cost,
                )
                for step in self.plan.steps
            )
        if any(not isinstance(item, DailyConstructionCost) for item in schedule):
            raise TypeError(
                "daily_construction_schedule must contain DailyConstructionCost values"
            )
        expected = tuple(
            (step.date, step.building, step.individual_cost)
            for step in self.plan.steps
        )
        actual = tuple(
            (item.date, item.building, item.cost)
            for item in schedule
        )
        if actual != expected:
            raise ValueError(
                "daily_construction_schedule must project the accepted plan steps"
            )
        object.__setattr__(self, "daily_construction_schedule", schedule)


def _diagnostic(
    diagnostic_code: str,
    category: PlannerDiagnosticCategory,
    explanation: str,
    *,
    affected_entities: tuple[BuildingKey, ...] = (),
    metadata: tuple[tuple[str, str], ...] = (),
) -> PlannerDiagnostic:
    return PlannerDiagnostic(
        diagnostic_code=diagnostic_code,
        category=category,
        canonical_explanation=explanation,
        affected_entities=affected_entities,
        metadata=metadata,
    )


def plan_build_order_result(
    city: FactionCity,
    graph: DependencyGraph,
    order: Iterable[BuildingKey],
    *,
    order_number: int = 1,
    starting_date: GameDate = GameDate(1, 1, 1),
) -> PlannerResult:
    """
    Convert one legal topological order into a dated, costed planner result.

    Failures retain the existing exception-based behavioral contract and carry
    canonical structured diagnostics.
    """
    normalized_order = tuple(order)

    if city.faction != graph.faction:
        explanation = (
            f"City faction {city.faction!r} does not match graph faction "
            f"{graph.faction!r}"
        )
        raise PlanningFailure(
            explanation,
            diagnostics=(
                _diagnostic(
                    "PLANNER_FACTION_MISMATCH",
                    PlannerDiagnosticCategory.INVALID_REQUEST,
                    explanation,
                    metadata=(
                        ("city_faction", city.faction),
                        ("graph_faction", graph.faction),
                    ),
                ),
            ),
        )

    if not is_valid_topological_order(graph, normalized_order):
        explanation = f"Order is not valid for target {graph.target}"
        raise InvalidBuildOrderError(
            explanation,
            diagnostics=(
                _diagnostic(
                    "PLANNER_INVALID_BUILD_ORDER",
                    PlannerDiagnosticCategory.INVALID_BUILD_ORDER,
                    explanation,
                    affected_entities=(graph.target, *normalized_order),
                    metadata=(("target", str(graph.target)),),
                ),
            ),
        )

    cumulative = ResourceCost()
    steps: list[BuildStep] = []

    for index, key in enumerate(normalized_order):
        try:
            building = city.buildings[key]
        except KeyError as exc:
            explanation = f"Graph node {key} is absent from the city"
            raise PlanningFailure(
                explanation,
                diagnostics=(
                    _diagnostic(
                        "PLANNER_GRAPH_NODE_MISSING_FROM_CITY",
                        PlannerDiagnosticCategory.DATA_INTEGRITY,
                        explanation,
                        affected_entities=(key,),
                        metadata=(("graph_target", str(graph.target)),),
                    ),
                ),
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

    return PlannerResult(
        plan=BuildPlan(
            faction=city.faction,
            target=graph.target,
            order_number=order_number,
            steps=tuple(steps),
            total_cost=cumulative,
            starting_date=starting_date,
        )
    )


def plan_build_order(
    city: FactionCity,
    graph: DependencyGraph,
    order: Iterable[BuildingKey],
    *,
    order_number: int = 1,
    starting_date: GameDate = GameDate(1, 1, 1),
) -> BuildPlan:
    """
    Compatibility interface returning the historical BuildPlan value.

    New callers that need success diagnostics should use plan_build_order_result.
    """
    return plan_build_order_result(
        city,
        graph,
        order,
        order_number=order_number,
        starting_date=starting_date,
    ).plan


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
        explanation = "plan set cannot be empty"
        raise PlanningFailure(
            explanation,
            diagnostics=(
                _diagnostic(
                    "PLANNER_EMPTY_PLAN_SET",
                    PlannerDiagnosticCategory.CONSISTENCY,
                    explanation,
                ),
            ),
        )

    first = normalized[0]
    seen_orders: set[tuple[BuildingKey, ...]] = set()

    for plan in normalized:
        checks = (
            (
                plan.faction != first.faction,
                "PLANNER_PLAN_SET_MULTIPLE_FACTIONS",
                "plan set contains multiple factions",
            ),
            (
                plan.target != first.target,
                "PLANNER_PLAN_SET_MULTIPLE_TARGETS",
                "plan set contains multiple targets",
            ),
            (
                plan.starting_date != first.starting_date,
                "PLANNER_PLAN_SET_MULTIPLE_STARTING_DATES",
                "plan set contains multiple starting dates",
            ),
            (
                plan.build_actions != first.build_actions,
                "PLANNER_PLAN_SET_INCONSISTENT_ACTION_COUNTS",
                "plan set has inconsistent action counts",
            ),
            (
                plan.total_cost != first.total_cost,
                "PLANNER_PLAN_SET_INCONSISTENT_TOTAL_COSTS",
                "plan set has inconsistent total costs",
            ),
            (
                plan.completion_date != first.completion_date,
                "PLANNER_PLAN_SET_INCONSISTENT_COMPLETION_DATES",
                "plan set has inconsistent completion dates",
            ),
            (
                plan.order in seen_orders,
                "PLANNER_PLAN_SET_DUPLICATE_ORDER",
                "plan set contains duplicate build orders",
            ),
        )
        for failed, code, explanation in checks:
            if failed:
                raise PlanningFailure(
                    explanation,
                    diagnostics=(
                        _diagnostic(
                            code,
                            PlannerDiagnosticCategory.CONSISTENCY,
                            explanation,
                            affected_entities=(plan.target,),
                        ),
                    ),
                )

        seen_orders.add(plan.order)
