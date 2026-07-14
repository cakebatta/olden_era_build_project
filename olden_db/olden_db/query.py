from __future__ import annotations

from dataclasses import dataclass

from .database import LoadedGameData, load_default_game_data
from .graph import build_dependency_graph, iter_topological_orders
from .models import BuildingKey, BuildingLevel, FactionCity, ResourceCost
from .planner import BuildPlan, GameDate, plan_build_order


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

    def get_building(self, faction: str, sid: str, level: int) -> BuildingLevel:
        city = self._get_city(faction)
        key = self._make_key(faction, sid, level)
        try:
            return city.buildings[key]
        except KeyError as exc:
            raise UnknownBuildingError(
                f"Unknown building: faction={faction!r}, sid={sid!r}, level={level}"
            ) from exc

    def get_prerequisites(self, faction: str, sid: str, level: int) -> tuple[BuildingLevel, ...]:
        city = self._get_city(faction)
        building = self.get_building(faction, sid, level)
        return tuple(
            city.buildings[key]
            for key in sorted(building.prerequisites, key=lambda item: (item.sid, item.level))
        )

    def generate_build_plan(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        starting_date: GameDate = GameDate(1, 1, 1),
    ) -> BuildPlan:
        city, graph = self._build_graph(faction, sid, level)
        order = next(iter_topological_orders(graph))
        return plan_build_order(city, graph, order, starting_date=starting_date)

    def get_cumulative_cost(self, faction: str, sid: str, level: int) -> ResourceCost:
        return self.generate_build_plan(faction, sid, level).total_cost

    def enumerate_build_orders(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        max_orders: int | None = None,
    ) -> tuple[tuple[BuildingKey, ...], ...]:
        _, graph = self._build_graph(faction, sid, level)
        return tuple(iter_topological_orders(graph, max_orders=max_orders))

    def _get_city(self, faction: str) -> FactionCity:
        if not faction:
            raise QueryError("faction cannot be empty")
        try:
            return self._data.cities.city(faction)
        except KeyError as exc:
            raise UnknownFactionError(f"Unknown faction: {faction!r}") from exc

    def _build_graph(self, faction: str, sid: str, level: int):
        city = self._get_city(faction)
        building = self.get_building(faction, sid, level)
        return city, build_dependency_graph(city, building.key)

    @staticmethod
    def _make_key(faction: str, sid: str, level: int) -> BuildingKey:
        if not sid:
            raise QueryError("sid cannot be empty")
        if level < 1:
            raise QueryError("level must be at least 1")
        return BuildingKey(faction=faction, sid=sid, level=level)
