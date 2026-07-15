from __future__ import annotations

from dataclasses import dataclass, field

from olden_db.models import BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan
from olden_db.scenario import PlanningScenario, PrerequisiteStatus


@dataclass(slots=True)
class PlannerState:
    """Explicit target, scenario, and generated-result state."""

    selected_faction: str | None = None
    selected_building_sid: str | None = None
    selected_level: int | None = None
    active_scenario: PlanningScenario = field(default_factory=PlanningScenario)
    scenario_candidates: tuple[BuildingLevel, ...] = ()
    current_building: BuildingLevel | None = None
    current_prerequisite_statuses: tuple[PrerequisiteStatus, ...] = ()
    current_plan: BuildPlan | None = None
    current_cumulative_cost: ResourceCost | None = None
    current_build_orders: tuple[tuple[object, ...], ...] = ()

    @property
    def has_complete_target(self) -> bool:
        return (
            self.selected_faction is not None
            and self.selected_building_sid is not None
            and self.selected_level is not None
        )

    @property
    def is_canonical_mode(self) -> bool:
        return not self.active_scenario.starting_building_overrides

    @property
    def override_count(self) -> int:
        return len(self.active_scenario.starting_building_overrides)

    def select_faction(self, faction: str, candidates: tuple[BuildingLevel, ...]) -> None:
        self.selected_faction = faction
        self.selected_building_sid = None
        self.selected_level = None
        self.active_scenario = PlanningScenario()
        self.scenario_candidates = candidates
        self.clear_results()

    def select_building(self, sid: str) -> None:
        self.selected_building_sid = sid
        self.selected_level = None
        self.clear_results()

    def select_level(self, level: int) -> None:
        self.selected_level = level
        self.clear_results()

    def replace_scenario(self, scenario: PlanningScenario) -> None:
        self.active_scenario = scenario
        self.clear_results()

    def store_results(
        self,
        *,
        building: BuildingLevel,
        prerequisite_statuses: tuple[PrerequisiteStatus, ...],
        plan: BuildPlan,
        cumulative_cost: ResourceCost,
        build_orders: tuple[tuple[object, ...], ...],
    ) -> None:
        self.current_building = building
        self.current_prerequisite_statuses = prerequisite_statuses
        self.current_plan = plan
        self.current_cumulative_cost = cumulative_cost
        self.current_build_orders = build_orders

    def clear_results(self) -> None:
        self.current_building = None
        self.current_prerequisite_statuses = ()
        self.current_plan = None
        self.current_cumulative_cost = None
        self.current_build_orders = ()
