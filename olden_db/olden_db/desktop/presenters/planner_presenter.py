from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from olden_db.models import BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan
from olden_db.query import PlanningQueryService, QueryError

from ..formatting import format_faction_status
from ..state import PlannerState


class PlannerViewContract(Protocol):
    def set_event_handlers(self, *, on_faction_changed: Callable[[str], None], on_building_changed: Callable[[str], None], on_level_changed: Callable[[int], None], on_generate_plan: Callable[[], None]) -> None: ...
    def set_factions(self, factions: tuple[str, ...]) -> None: ...
    def set_buildings(self, buildings: tuple[str, ...]) -> None: ...
    def set_levels(self, levels: tuple[int, ...]) -> None: ...
    def clear_building_selection(self) -> None: ...
    def clear_level_selection(self) -> None: ...
    def set_generate_enabled(self, enabled: bool) -> None: ...
    def clear_results(self) -> None: ...
    def show_target(self, building: BuildingLevel) -> None: ...
    def show_prerequisites(self, prerequisites: tuple[BuildingLevel, ...]) -> None: ...
    def show_plan(self, plan: BuildPlan, cumulative_cost: ResourceCost) -> None: ...
    def show_error(self, message: str) -> None: ...


class PlannerPresenter:
    def __init__(self, service: PlanningQueryService, state: PlannerState, view: PlannerViewContract, set_status: Callable[[str], None]) -> None:
        self._service = service
        self._state = state
        self._view = view
        self._set_status = set_status

    def initialize(self) -> None:
        self._view.set_event_handlers(on_faction_changed=self.on_faction_changed, on_building_changed=self.on_building_changed, on_level_changed=self.on_level_changed, on_generate_plan=self.on_generate_plan)
        factions = self._service.list_factions()
        self._view.set_factions(factions)
        self._view.clear_building_selection()
        self._view.clear_level_selection()
        self._view.set_generate_enabled(False)
        self._view.clear_results()
        self._set_status(format_faction_status(len(factions)))

    def on_faction_changed(self, faction: str) -> None:
        self._clear_generated_results()
        self._view.clear_building_selection()
        self._view.clear_level_selection()
        self._view.set_generate_enabled(False)
        try:
            buildings = self._service.list_buildings(faction)
        except QueryError as exc:
            self._set_status(f"Request could not be completed: {exc}")
            return
        self._state.select_faction(faction)
        self._view.set_buildings(buildings)
        self._set_status(f"Faction selected: {faction}. Select a building.")

    def on_building_changed(self, sid: str) -> None:
        faction = self._state.selected_faction
        if faction is None:
            self._set_status("Select a faction before selecting a building.")
            return
        self._clear_generated_results()
        self._view.clear_level_selection()
        self._view.set_generate_enabled(False)
        try:
            levels = self._service.list_building_levels(faction, sid)
        except QueryError as exc:
            self._set_status(f"Request could not be completed: {exc}")
            return
        self._state.select_building(sid)
        self._view.set_levels(levels)
        self._set_status(f"Building selected: {sid}. Select a level.")

    def on_level_changed(self, level: int) -> None:
        if self._state.selected_faction is None or self._state.selected_building_sid is None:
            self._set_status("Select a faction and building before selecting a level.")
            self._view.set_generate_enabled(False)
            return
        self._clear_generated_results()
        self._state.select_level(level)
        self._view.set_generate_enabled(self._state.has_complete_target)
        self._set_status(f"Target selected: {self._state.selected_faction}/{self._state.selected_building_sid} level {level}.")

    def on_generate_plan(self) -> None:
        if not self._state.has_complete_target:
            self._view.set_generate_enabled(False)
            self._clear_generated_results()
            self._set_status("Select a faction, building, and level first.")
            return
        faction = self._state.selected_faction
        sid = self._state.selected_building_sid
        level = self._state.selected_level
        assert faction is not None and sid is not None and level is not None
        self._clear_generated_results()
        try:
            building = self._service.get_building(faction, sid, level)
            prerequisites = self._service.get_prerequisites(faction, sid, level)
            plan = self._service.generate_build_plan(faction, sid, level)
            cumulative_cost = self._service.get_cumulative_cost(faction, sid, level)
        except QueryError as exc:
            message = f"Request could not be completed: {exc}"
            self._view.show_error(message)
            self._set_status(message)
            return
        if cumulative_cost != plan.total_cost:
            raise RuntimeError("Query Layer cumulative cost did not match the generated plan")
        self._state.store_results(building=building, prerequisites=prerequisites, plan=plan, cumulative_cost=cumulative_cost)
        self._view.show_target(building)
        self._view.show_prerequisites(prerequisites)
        self._view.show_plan(plan, cumulative_cost)
        if plan.build_actions:
            self._set_status(f"Build plan generated successfully: {plan.build_actions} construction actions.")
        else:
            self._set_status("Target is constructed at game start; no construction actions are required.")

    def _clear_generated_results(self) -> None:
        self._state.clear_results()
        self._view.clear_results()
