from __future__ import annotations

from dataclasses import dataclass

from .comparison import PlanComparison, compare_build_plans
from .database import LoadedGameData, load_default_game_data
from .graph import DependencyGraph, build_dependency_graph, iter_topological_orders
from .models import BuildingKey, BuildingLevel, FactionCity, ResourceCost
from .planner import BuildPlan, GameDate, plan_build_order
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
        """Return canonical faction identifiers in deterministic order."""
        return tuple(sorted(self._data.cities.cities))

    def list_buildings(self, faction: str) -> tuple[str, ...]:
        """Return unique canonical building SIDs for one faction."""
        city = self._get_city(faction)
        return tuple(sorted({key.sid for key in city.buildings}))

    def list_building_levels(self, faction: str, sid: str) -> tuple[int, ...]:
        """Return valid levels for one canonical building SID."""
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
        """Return effective starting status for each direct prerequisite."""
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
        """Generate and compare two plans using right-minus-left semantics."""
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
