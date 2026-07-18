from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan, PlanningFailure
from olden_db.query import PlanningQueryService, QueryError
from olden_db.scenario import (
    DuplicateStartingBuildingOverrideError,
    InvalidStartingBuildingOverrideError,
    PlanningScenario,
    PrerequisiteStatus,
    ScenarioError,
    StartingBuildingOverride,
)

from ..formatting import format_faction_status
from ..planner_diagnostics import (
    PlannerDiagnosticPresentation,
    adapt_planner_diagnostics,
)
from ..state import PlannerState

SCENARIO_ERRORS = (
    ScenarioError,
    DuplicateStartingBuildingOverrideError,
    InvalidStartingBuildingOverrideError,
)


class PlannerViewContract(Protocol):
    def set_event_handlers(self, **handlers) -> None: ...
    def set_factions(self, factions: tuple[str, ...]) -> None: ...
    def set_buildings(self, buildings: tuple[str, ...]) -> None: ...
    def set_levels(self, levels: tuple[int, ...]) -> None: ...
    def clear_building_selection(self) -> None: ...
    def clear_level_selection(self) -> None: ...
    def set_generate_enabled(self, enabled: bool) -> None: ...
    def set_starting_buildings(
        self,
        buildings: tuple[BuildingLevel, ...],
        scenario: PlanningScenario,
    ) -> None: ...
    def clear_starting_buildings(self) -> None: ...
    def set_planning_mode(self, override_count: int) -> None: ...
    def clear_results(self) -> None: ...
    def show_target(self, building: BuildingLevel) -> None: ...
    def show_prerequisites(
        self,
        statuses: tuple[PrerequisiteStatus, ...],
    ) -> None: ...
    def show_plan(
        self,
        plan: BuildPlan,
        cumulative_cost: ResourceCost,
    ) -> None: ...
    def show_error(self, message: str) -> None: ...
    def set_constraint_diagnostics(
        self,
        diagnostics: tuple[PlannerDiagnosticPresentation, ...],
    ) -> None: ...


class PlannerPresenter:
    def __init__(
        self,
        service: PlanningQueryService,
        state: PlannerState,
        view: PlannerViewContract,
        set_status: Callable[[str], None],
        on_context_changed: Callable[[], None] | None = None,
    ) -> None:
        self._service = service
        self._state = state
        self._view = view
        self._set_status = set_status
        self._on_context_changed = on_context_changed or (lambda: None)

    def initialize(self) -> None:
        self._view.set_event_handlers(
            on_faction_changed=self.on_faction_changed,
            on_building_changed=self.on_building_changed,
            on_level_changed=self.on_level_changed,
            on_generate_plan=self.on_generate_plan,
            on_starting_building_changed=self.on_starting_building_changed,
            on_reset_scenario=self.on_reset_scenario,
        )
        factions = self._service.list_factions()
        self._view.set_factions(factions)
        self._view.clear_building_selection()
        self._view.clear_level_selection()
        self._view.clear_starting_buildings()
        self._view.set_generate_enabled(False)
        self._view.set_planning_mode(0)
        self._view.clear_results()
        self._set_status(format_faction_status(len(factions)))

    def on_faction_changed(self, faction: str) -> None:
        self._clear_generated_results()
        self._view.clear_building_selection()
        self._view.clear_level_selection()
        self._view.set_generate_enabled(False)
        try:
            sids = self._service.list_buildings(faction)
            candidates = self._load_candidates(faction, sids)
        except QueryError as exc:
            self._show_error(exc)
            return
        self._state.select_faction(faction, candidates)
        self._view.set_buildings(sids)
        self._view.set_starting_buildings(
            candidates,
            self._state.active_scenario,
        )
        self._view.set_planning_mode(0)
        self._on_context_changed()
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
            self._show_error(exc)
            return
        self._state.select_building(sid)
        self._view.set_levels(levels)
        self._on_context_changed()
        self._set_status(f"Building selected: {sid}. Select a level.")

    def on_level_changed(self, level: int) -> None:
        if (
            self._state.selected_faction is None
            or self._state.selected_building_sid is None
        ):
            self._view.set_generate_enabled(False)
            return
        self._clear_generated_results()
        self._state.select_level(level)
        self._view.set_generate_enabled(self._state.has_complete_target)
        self._on_context_changed()
        self._set_status(
            f"Target selected: {self._state.selected_faction}/"
            f"{self._state.selected_building_sid} level {level}."
        )

    def on_starting_building_changed(
        self,
        key: BuildingKey,
        available: bool,
    ) -> None:
        candidate = next(
            (
                item
                for item in self._state.scenario_candidates
                if item.key == key
            ),
            None,
        )
        if candidate is None:
            return

        regenerate = self._state.current_plan is not None
        overrides = {
            item.building: item.available_at_start
            for item in self._state.active_scenario.starting_building_overrides
        }
        if available == candidate.constructed_on_start:
            overrides.pop(key, None)
        else:
            overrides[key] = available

        try:
            scenario = PlanningScenario(
                tuple(
                    StartingBuildingOverride(building, value)
                    for building, value in overrides.items()
                )
            )
        except SCENARIO_ERRORS as exc:
            self._show_error(exc)
            return

        self._state.replace_scenario(scenario)
        self._view.set_starting_buildings(
            self._state.scenario_candidates,
            scenario,
        )
        self._view.set_planning_mode(self._state.override_count)
        self._view.clear_results()
        self._on_context_changed()

        if regenerate and self._state.has_complete_target:
            self.on_generate_plan()

    def on_reset_scenario(self) -> None:
        regenerate = self._state.current_plan is not None
        scenario = PlanningScenario()
        self._state.replace_scenario(scenario)
        self._view.set_starting_buildings(
            self._state.scenario_candidates,
            scenario,
        )
        self._view.set_planning_mode(0)
        self._view.clear_results()
        self._on_context_changed()

        if regenerate and self._state.has_complete_target:
            self.on_generate_plan()

    def on_generate_plan(self) -> None:
        if not self._state.has_complete_target:
            return

        faction = self._state.selected_faction
        sid = self._state.selected_building_sid
        level = self._state.selected_level
        assert faction is not None
        assert sid is not None
        assert level is not None

        self._clear_generated_results()
        scenario = self._state.active_scenario
        try:
            building = self._service.get_building(faction, sid, level)
            statuses = self._service.get_prerequisite_statuses(
                faction,
                sid,
                level,
                scenario=scenario,
            )
            plan = self._service.generate_build_plan(
                faction,
                sid,
                level,
                scenario=scenario,
            )
            cost = self._service.get_cumulative_cost(
                faction,
                sid,
                level,
                scenario=scenario,
            )
            orders = self._service.enumerate_build_orders(
                faction,
                sid,
                level,
                scenario=scenario,
            )
        except (QueryError, PlanningFailure, *SCENARIO_ERRORS) as exc:
            self._show_error(exc)
            return

        self._state.store_results(
            building=building,
            prerequisite_statuses=statuses,
            plan=plan,
            cumulative_cost=cost,
            build_orders=orders,
        )
        self._view.show_target(building)
        self._view.show_prerequisites(statuses)
        self._view.show_plan(plan, cost)

    def _load_candidates(self, faction, sids):
        return tuple(
            sorted(
                (
                    self._service.get_building(faction, sid, level)
                    for sid in sids
                    for level in self._service.list_building_levels(
                        faction,
                        sid,
                    )
                ),
                key=lambda item: (item.key.sid, item.key.level),
            )
        )

    def _clear_generated_results(self) -> None:
        self._state.clear_results()
        self._view.clear_results()

    def _show_error(self, exc: Exception) -> None:
        self._state.clear_results()
        message = f"Request could not be completed: {exc}"
        self._view.show_error(message)

        diagnostics = getattr(exc, "diagnostics", ())
        if diagnostics:
            self._view.set_constraint_diagnostics(
                adapt_planner_diagnostics(tuple(diagnostics))
            )

        self._set_status(message)
