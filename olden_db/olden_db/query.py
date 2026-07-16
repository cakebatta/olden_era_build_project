from __future__ import annotations

from dataclasses import dataclass

from .comparison import PlanComparison, compare_build_plans
from .database import LoadedGameData, load_default_game_data
from .decision_summary import DecisionSummary, summarize_plan_comparison
from .graph import DependencyGraph, build_dependency_graph, iter_topological_orders
from .income_timeline import calculate_income_timeline
from .models import BuildingKey, BuildingLevel, FactionCity, ResourceCost
from .planner import BuildPlan, GameDate, plan_build_order
from .recruitment_stock import calculate_recruitment_stock
from .resource_ledger import (
    RecruitmentAction,
    ResourceLedger,
    build_resource_ledger,
)
from .scenario import (
    PlanningScenario,
    PrerequisiteStatus,
    resolve_effective_starting_buildings,
)


class QueryError(ValueError):
    """Base exception for invalid Query Layer requests."""


class UnknownFactionError(QueryError):
    """Raised when a requested faction is not present."""


class UnknownBuildingError(QueryError):
    """Raised when a requested building level is not present."""


@dataclass(frozen=True, slots=True)
class PlanningQueryService:
    """Stable public interface for deterministic building-planning queries."""

    _data: LoadedGameData

    @classmethod
    def from_default_game_data(cls) -> "PlanningQueryService":
        """Create a ready-to-use service from the canonical game data."""
        return cls(load_default_game_data())

    def list_factions(self) -> tuple[str, ...]:
        return tuple(sorted(self._data.cities.cities))

    def list_buildings(self, faction: str) -> tuple[str, ...]:
        city = self._get_city(faction)
        return tuple(sorted({key.sid for key in city.buildings}))

    def list_building_levels(self, faction: str, sid: str) -> tuple[int, ...]:
        city = self._get_city(faction)
        if not sid:
            raise QueryError("sid cannot be empty")
        levels = tuple(sorted(key.level for key in city.buildings if key.sid == sid))
        if not levels:
            raise UnknownBuildingError(
                f"Unknown building SID: faction={faction!r}, sid={sid!r}"
            )
        return levels

    def get_building(self, faction: str, sid: str, level: int) -> BuildingLevel:
        city = self._get_city(faction)
        key = self._make_key(faction, sid, level)
        try:
            return city.buildings[key]
        except KeyError as exc:
            raise UnknownBuildingError(
                f"Unknown building: faction={faction!r}, sid={sid!r}, level={level}"
            ) from exc

    def get_prerequisites(
        self,
        faction: str,
        sid: str,
        level: int,
    ) -> tuple[BuildingLevel, ...]:
        city = self._get_city(faction)
        building = self.get_building(faction, sid, level)
        return tuple(
            city.buildings[key]
            for key in sorted(
                building.prerequisites,
                key=lambda item: (item.sid, item.level),
            )
        )

    def get_prerequisite_statuses(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        scenario: PlanningScenario | None = None,
    ) -> tuple[PrerequisiteStatus, ...]:
        city = self._get_city(faction)
        building = self.get_building(faction, sid, level)
        effective_starting = self._effective_starting_buildings(city, scenario)
        return tuple(
            PrerequisiteStatus(
                building=city.buildings[key],
                available_at_start=key in effective_starting,
                overridden=(
                    (key in effective_starting)
                    != city.buildings[key].constructed_on_start
                ),
            )
            for key in sorted(
                building.prerequisites,
                key=lambda item: (item.sid, item.level),
            )
        )

    def generate_build_plan(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        starting_date: GameDate = GameDate(1, 1, 1),
        scenario: PlanningScenario | None = None,
    ) -> BuildPlan:
        city, graph = self._build_graph(faction, sid, level, scenario=scenario)
        order = next(iter_topological_orders(graph))
        return plan_build_order(city, graph, order, starting_date=starting_date)

    def get_cumulative_cost(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        scenario: PlanningScenario | None = None,
    ) -> ResourceCost:
        return self.generate_build_plan(
            faction,
            sid,
            level,
            scenario=scenario,
        ).total_cost

    def enumerate_build_orders(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        max_orders: int | None = None,
        scenario: PlanningScenario | None = None,
    ) -> tuple[tuple[BuildingKey, ...], ...]:
        _, graph = self._build_graph(faction, sid, level, scenario=scenario)
        return tuple(iter_topological_orders(graph, max_orders=max_orders))

    def compare_plans(
        self,
        left_faction: str,
        left_sid: str,
        left_level: int,
        *,
        right_faction: str,
        right_sid: str,
        right_level: int,
        left_scenario: PlanningScenario | None = None,
        right_scenario: PlanningScenario | None = None,
        starting_date: GameDate = GameDate(1, 1, 1),
    ) -> PlanComparison:
        left_plan = self.generate_build_plan(
            left_faction,
            left_sid,
            left_level,
            starting_date=starting_date,
            scenario=left_scenario,
        )
        right_plan = self.generate_build_plan(
            right_faction,
            right_sid,
            right_level,
            starting_date=starting_date,
            scenario=right_scenario,
        )
        return compare_build_plans(left_plan, right_plan)

    def generate_decision_summary(
        self,
        left_faction: str,
        left_sid: str,
        left_level: int,
        *,
        right_faction: str,
        right_sid: str,
        right_level: int,
        left_scenario: PlanningScenario | None = None,
        right_scenario: PlanningScenario | None = None,
        starting_date: GameDate = GameDate(1, 1, 1),
    ) -> DecisionSummary:
        comparison = self.compare_plans(
            left_faction,
            left_sid,
            left_level,
            right_faction=right_faction,
            right_sid=right_sid,
            right_level=right_level,
            left_scenario=left_scenario,
            right_scenario=right_scenario,
            starting_date=starting_date,
        )
        return summarize_plan_comparison(comparison)

    def generate_resource_ledger(
        self,
        faction: str,
        sid: str,
        level: int,
        recruitment_actions: tuple[RecruitmentAction, ...],
        starting_resources: ResourceCost,
        *,
        starting_date: GameDate = GameDate(1, 1, 1),
        scenario: PlanningScenario | None = None,
    ) -> ResourceLedger:
        """Generate one scenario-consistent income, construction, and recruitment ledger."""
        city = self._get_city(faction)
        building = self.get_building(faction, sid, level)
        effective_starting = self._effective_starting_buildings(city, scenario)

        graph = build_dependency_graph(
            city,
            building.key,
            starting_buildings=effective_starting,
        )
        order = next(iter_topological_orders(graph))
        plan = plan_build_order(
            city,
            graph,
            order,
            starting_date=starting_date,
        )

        through_date = plan.completion_date
        for action in recruitment_actions:
            if (
                isinstance(action, RecruitmentAction)
                and action.date.day_index > through_date.day_index
            ):
                through_date = action.date

        income_timeline = calculate_income_timeline(
            city,
            plan,
            through_date=through_date,
            starting_buildings=effective_starting,
        )
        stock = calculate_recruitment_stock(
            city,
            plan,
            through_date=through_date,
            starting_buildings=effective_starting,
        )
        return build_resource_ledger(
            city,
            plan,
            stock,
            recruitment_actions,
            starting_resources,
            starting_buildings=effective_starting,
            income_timeline=income_timeline,
        )

    def _get_city(self, faction: str) -> FactionCity:
        if not faction:
            raise QueryError("faction cannot be empty")
        try:
            return self._data.cities.city(faction)
        except KeyError as exc:
            raise UnknownFactionError(f"Unknown faction: {faction!r}") from exc

    def _build_graph(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        scenario: PlanningScenario | None = None,
    ) -> tuple[FactionCity, DependencyGraph]:
        city = self._get_city(faction)
        building = self.get_building(faction, sid, level)
        starting_buildings = (
            None
            if scenario is None
            else resolve_effective_starting_buildings(city, scenario)
        )
        return city, build_dependency_graph(
            city,
            building.key,
            starting_buildings=starting_buildings,
        )

    @staticmethod
    def _effective_starting_buildings(
        city: FactionCity,
        scenario: PlanningScenario | None,
    ) -> frozenset[BuildingKey]:
        if scenario is not None:
            return resolve_effective_starting_buildings(city, scenario)
        return frozenset(
            key
            for key, building in city.buildings.items()
            if building.constructed_on_start
        )

    @staticmethod
    def _make_key(faction: str, sid: str, level: int) -> BuildingKey:
        if not sid:
            raise QueryError("sid cannot be empty")
        if level < 1:
            raise QueryError("level must be at least 1")
        return BuildingKey(faction=faction, sid=sid, level=level)
