from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from olden_db.query import PlanningQueryService, QueryError

from ..formatting import format_faction_status
from ..state import PlannerState


class PlannerViewContract(Protocol):
    """View operations required by the target-selection presenter."""

    def set_event_handlers(self, *, on_faction_changed: Callable[[str], None], on_building_changed: Callable[[str], None], on_level_changed: Callable[[int], None], on_generate_plan: Callable[[], None]) -> None: ...
    def set_factions(self, factions: tuple[str, ...]) -> None: ...
    def set_buildings(self, buildings: tuple[str, ...]) -> None: ...
    def set_levels(self, levels: tuple[int, ...]) -> None: ...
    def clear_building_selection(self) -> None: ...
    def clear_level_selection(self) -> None: ...
    def set_generate_enabled(self, enabled: bool) -> None: ...


class PlannerPresenter:
    """Coordinate target discovery, selection state, and view updates."""

    def __init__(self, service: PlanningQueryService, state: PlannerState, view: PlannerViewContract, set_status: Callable[[str], None]) -> None:
        self._service = service
        self._state = state
        self._view = view
        self._set_status = set_status

    def initialize(self) -> None:
        self._view.set_event_handlers(
            on_faction_changed=self.on_faction_changed,
            on_building_changed=self.on_building_changed,
            on_level_changed=self.on_level_changed,
            on_generate_plan=self.on_generate_plan,
        )
        factions = self._service.list_factions()
        self._view.set_factions(factions)
        self._view.clear_building_selection()
        self._view.clear_level_selection()
        self._view.set_generate_enabled(False)
        self._set_status(format_faction_status(len(factions)))

    def on_faction_changed(self, faction: str) -> None:
        self._state.select_faction(faction)
        self._view.clear_building_selection()
        self._view.clear_level_selection()
        self._view.set_generate_enabled(False)
        try:
            buildings = self._service.list_buildings(faction)
        except QueryError as exc:
            self._set_status(f"Request could not be completed: {exc}")
            return
        self._view.set_buildings(buildings)
        self._set_status(f"Faction selected: {faction}. Select a building.")

    def on_building_changed(self, sid: str) -> None:
        faction = self._state.selected_faction
        if faction is None:
            self._set_status("Select a faction before selecting a building.")
            return
        self._state.select_building(sid)
        self._view.clear_level_selection()
        self._view.set_generate_enabled(False)
        try:
            levels = self._service.list_building_levels(faction, sid)
        except QueryError as exc:
            self._set_status(f"Request could not be completed: {exc}")
            return
        self._view.set_levels(levels)
        self._set_status(f"Building selected: {sid}. Select a level.")

    def on_level_changed(self, level: int) -> None:
        if self._state.selected_faction is None or self._state.selected_building_sid is None:
            self._set_status("Select a faction and building before selecting a level.")
            self._view.set_generate_enabled(False)
            return
        self._state.select_level(level)
        self._view.set_generate_enabled(self._state.has_complete_target)
        self._set_status(f"Target selected: {self._state.selected_faction}/{self._state.selected_building_sid} level {level}.")

    def on_generate_plan(self) -> None:
        if not self._state.has_complete_target:
            self._view.set_generate_enabled(False)
            self._set_status("Select a faction, building, and level first.")
            return
        self._set_status("Build plan generation will be implemented in the next milestone.")
