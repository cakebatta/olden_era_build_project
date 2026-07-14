from __future__ import annotations

from dataclasses import dataclass

from olden_db.models import BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan


@dataclass(slots=True)
class PlannerState:
    """Explicit target selection and generated-result state."""

    selected_faction: str | None = None
    selected_building_sid: str | None = None
    selected_level: int | None = None
    current_building: BuildingLevel | None = None
    current_prerequisites: tuple[BuildingLevel, ...] = ()
    current_plan: BuildPlan | None = None
    current_cumulative_cost: ResourceCost | None = None

    @property
    def has_complete_target(self) -> bool:
        return (
            self.selected_faction is not None
            and self.selected_building_sid is not None
            and self.selected_level is not None
        )

    def select_faction(self, faction: str) -> None:
        self.selected_faction = faction
        self.selected_building_sid = None
        self.selected_level = None
        self.clear_results()

    def select_building(self, sid: str) -> None:
        self.selected_building_sid = sid
        self.selected_level = None
        self.clear_results()

    def select_level(self, level: int) -> None:
        self.selected_level = level
        self.clear_results()

    def store_results(self, *, building: BuildingLevel, prerequisites: tuple[BuildingLevel, ...], plan: BuildPlan, cumulative_cost: ResourceCost) -> None:
        self.current_building = building
        self.current_prerequisites = prerequisites
        self.current_plan = plan
        self.current_cumulative_cost = cumulative_cost

    def clear_results(self) -> None:
        self.current_building = None
        self.current_prerequisites = ()
        self.current_plan = None
        self.current_cumulative_cost = None
