from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from olden_db.models import BuildingKey, BuildingLevel
from olden_db.planner import GameDate
from olden_db.planning_execution import PlanningExecutionCoordinator
from olden_db.planning_workspace import (
    DEFAULT_BASE_PLAN_ID,
    PlanningExecutionStatus,
    PlanningSelection,
    PlanningWorkspace,
    PlanningWorkspaceSnapshot,
)
from olden_db.query import PlanningQueryService, QueryError
from olden_db.scenario import (
    DuplicateStartingBuildingOverrideError,
    InvalidStartingBuildingOverrideError,
    PlanningScenario,
    ScenarioError,
    StartingBuildingOverride,
)

from ..formatting import format_faction_status
from ..planner_diagnostics import adapt_planner_diagnostics
from ..state import PlannerState
from ..workspace_presentation import PlanningWorkspacePresentation


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
    def set_starting_date(self, date: GameDate) -> None: ...
    def set_selection_values(self, faction: str, sid: str, level: int) -> None: ...
    def set_starting_buildings(
        self,
        buildings: tuple[BuildingLevel, ...],
        scenario: PlanningScenario,
    ) -> None: ...
    def clear_starting_buildings(self) -> None: ...
    def set_planning_mode(self, override_count: int) -> None: ...
    def show_error(self, message: str) -> None: ...
    def render_workspace(
        self,
        presentation: PlanningWorkspacePresentation,
    ) -> None: ...


class PlannerPresenter:
    """Translate semantic desktop actions into one Planning Workspace lifecycle."""

    def __init__(
        self,
        service: PlanningQueryService,
        workspace: PlanningWorkspace,
        execution_coordinator: PlanningExecutionCoordinator,
        state: PlannerState,
        view: PlannerViewContract,
        set_status: Callable[[str], None],
        on_context_changed: Callable[[], None] | None = None,
    ) -> None:
        self._service = service
        self._workspace = workspace
        self._execution_coordinator = execution_coordinator
        self._state = state
        self._view = view
        self._set_status = set_status
        self._on_context_changed = on_context_changed or (lambda: None)

    def initialize(self) -> None:
        self._view.set_event_handlers(
            on_faction_changed=self.on_faction_changed,
            on_building_changed=self.on_building_changed,
            on_level_changed=self.on_level_changed,
            on_starting_date_changed=self.on_starting_date_changed,
            on_generate_plan=self.on_generate_plan,
            on_starting_building_changed=self.on_starting_building_changed,
            on_reset_scenario=self.on_reset_scenario,
        )
        factions = self._service.list_factions()
        self._view.set_factions(factions)
        self._view.clear_building_selection()
        self._view.clear_level_selection()
        self._view.clear_starting_buildings()
        self._view.set_starting_date(self._state.starting_date)
        self._view.set_generate_enabled(False)
        self._view.set_planning_mode(0)
        self._render_snapshot(self._workspace.snapshot())
        self._set_status(format_faction_status(len(factions)))

    def on_faction_changed(self, faction: str) -> None:
        self._view.clear_building_selection()
        self._view.clear_level_selection()
        try:
            sids = self._service.list_buildings(faction)
            candidates = self._load_candidates(faction, sids)
        except QueryError as exc:
            self._show_discovery_error(exc)
            return
        self._state.select_faction(faction, candidates)
        self._view.set_buildings(sids)
        self._view.set_starting_buildings(candidates, self._state.active_scenario)
        self._view.set_planning_mode(0)
        self._selection_became_incomplete()
        self._on_context_changed()
        self._set_status(f"Faction selected: {faction}. Select a building.")

    def on_building_changed(self, sid: str) -> None:
        faction = self._state.selected_faction
        if faction is None:
            self._set_status("Select a faction before selecting a building.")
            return
        self._view.clear_level_selection()
        try:
            levels = self._service.list_building_levels(faction, sid)
        except QueryError as exc:
            self._show_discovery_error(exc)
            return
        self._state.select_building(sid)
        self._view.set_levels(levels)
        self._selection_became_incomplete()
        self._on_context_changed()
        self._set_status(f"Building selected: {sid}. Select a level.")

    def on_level_changed(self, level: int) -> None:
        if (
            self._state.selected_faction is None
            or self._state.selected_building_sid is None
        ):
            return
        self._state.select_level(level)
        self._on_context_changed()
        self._submit_current_selection()

    def on_starting_date_changed(self, month: int, week: int, day: int) -> None:
        try:
            date = GameDate(month, week, day)
        except (TypeError, ValueError) as exc:
            self._set_status(f"Starting date is invalid: {exc}")
            return
        if date == self._state.starting_date:
            return
        self._state.starting_date = date
        self._on_context_changed()
        self._submit_current_selection()

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
            self._show_discovery_error(exc)
            return
        self._state.replace_scenario(scenario)
        self._view.set_starting_buildings(self._state.scenario_candidates, scenario)
        self._view.set_planning_mode(self._state.override_count)
        self._on_context_changed()
        self._submit_current_selection()

    def on_reset_scenario(self) -> None:
        scenario = PlanningScenario()
        if scenario == self._state.active_scenario:
            return
        self._state.replace_scenario(scenario)
        self._view.set_starting_buildings(self._state.scenario_candidates, scenario)
        self._view.set_planning_mode(0)
        self._on_context_changed()
        self._submit_current_selection()

    def on_generate_plan(self) -> None:
        """Compatibility callback for the hidden legacy action."""
        self._submit_current_selection()

    def apply_semantic_selection(
        self,
        *,
        faction: str,
        sid: str,
        level: int,
        starting_date: GameDate,
        scenario: PlanningScenario,
    ) -> None:
        """Apply a compound restored selection and execute it exactly once."""
        try:
            sids = self._service.list_buildings(faction)
            candidates = self._load_candidates(faction, sids)
            levels = self._service.list_building_levels(faction, sid)
        except QueryError as exc:
            self._show_discovery_error(exc)
            return
        if sid not in sids or level not in levels:
            self._show_discovery_error(
                ValueError("Restored planning target is unavailable.")
            )
            return
        self._state.select_faction(faction, candidates)
        self._state.select_building(sid)
        self._state.select_level(level)
        self._state.starting_date = starting_date
        self._state.replace_scenario(scenario)
        self._view.set_buildings(sids)
        self._view.set_levels(levels)
        self._view.set_selection_values(faction, sid, level)
        self._view.set_starting_date(starting_date)
        self._view.set_starting_buildings(candidates, scenario)
        self._view.set_planning_mode(self._state.override_count)
        self._on_context_changed()
        self._submit_current_selection()

    def _selection_became_incomplete(self) -> None:
        self._workspace.reset_selection(DEFAULT_BASE_PLAN_ID)
        self._state.clear_results()
        self._render_snapshot(self._workspace.snapshot())

    def _submit_current_selection(self) -> None:
        if not self._state.has_complete_target:
            self._selection_became_incomplete()
            return
        faction = self._state.selected_faction
        sid = self._state.selected_building_sid
        level = self._state.selected_level
        assert faction is not None
        assert sid is not None
        assert level is not None
        selection = PlanningSelection(
            faction=faction,
            target=BuildingKey(faction, sid, level),
            starting_date=self._state.starting_date,
            scenario=self._state.active_scenario,
        )
        before = self._workspace.base(DEFAULT_BASE_PLAN_ID)
        pending_snapshot = self._workspace.replace_selection(
            selection,
            DEFAULT_BASE_PLAN_ID,
        )
        pending_state = pending_snapshot.base(DEFAULT_BASE_PLAN_ID)
        if pending_state.selection_revision == before.selection_revision:
            self._render_snapshot(pending_snapshot)
            return
        self._state.clear_results()
        self._render_snapshot(pending_snapshot)
        self._set_status(f"Planning revision {pending_state.selection_revision}…")
        outcome = self._execution_coordinator.execute(
            self._workspace,
            DEFAULT_BASE_PLAN_ID,
        )
        self._render_snapshot(outcome.snapshot)

    def _render_snapshot(self, snapshot: PlanningWorkspaceSnapshot) -> None:
        base = snapshot.base(DEFAULT_BASE_PLAN_ID)
        result = base.accepted_result
        plan = result.plan if result is not None else None
        if (
            base.execution_status is PlanningExecutionStatus.FAILED
            and base.latest_failure is not None
        ):
            diagnostics = adapt_planner_diagnostics(base.latest_failure.diagnostics)
        elif result is not None:
            diagnostics = adapt_planner_diagnostics(result.diagnostics)
        else:
            diagnostics = ()
        if base.selection is None:
            selection_summary = "Complete faction, target, level, date, and scenario."
        else:
            selection_summary = (
                f"{base.selection.faction} / {base.selection.target.sid} "
                f"level {base.selection.target.level} / "
                f"starts {base.selection.starting_date}"
            )
        failure_message = (
            base.latest_failure.message
            if base.latest_failure is not None
            else None
        )
        if base.execution_status is PlanningExecutionStatus.PENDING:
            heading = "Planning in progress"
            detail = (
                "The current semantic selection is being evaluated."
                if not base.retains_previous_result
                else (
                    "The current semantic selection is being evaluated. "
                    "The displayed plan is the previous accepted result."
                )
            )
        elif base.execution_status is PlanningExecutionStatus.READY:
            heading = "Current plan ready"
            detail = f"Revision {base.selection_revision} is accepted."
        elif base.execution_status is PlanningExecutionStatus.FAILED:
            heading = "Current request failed"
            detail = (
                "The current selection could not be planned."
                if not base.retains_previous_result
                else (
                    "The current selection could not be planned. "
                    "The displayed plan is the previous accepted result."
                )
            )
        else:
            heading = "Planning selection incomplete"
            detail = (
                "Choose one canonical target to plan automatically."
                if not base.retains_previous_result
                else (
                    "Choose one canonical target to plan automatically. "
                    "The displayed plan is the previous accepted result."
                )
            )
        presentation = PlanningWorkspacePresentation(
            execution_status=base.execution_status,
            status_heading=heading,
            status_detail=detail,
            selection_summary=selection_summary,
            accepted_plan=plan,
            retained_previous_result=base.retains_previous_result,
            failure_message=failure_message,
            diagnostics=diagnostics,
            selection_revision=base.selection_revision,
            result_revision=base.result_revision,
        )
        if base.result_is_current and plan is not None:
            self._state.store_workspace_result(plan)
        else:
            self._state.clear_results()
        self._view.render_workspace(presentation)
        if base.execution_status is PlanningExecutionStatus.READY:
            self._set_status(
                f"Planning revision {base.selection_revision} completed."
            )
        elif base.execution_status is PlanningExecutionStatus.FAILED:
            self._set_status(
                "Current planning request failed"
                + (f": {failure_message}" if failure_message else ".")
            )

    def _load_candidates(
        self,
        faction: str,
        sids: tuple[str, ...],
    ) -> tuple[BuildingLevel, ...]:
        return tuple(
            sorted(
                (
                    self._service.get_building(faction, sid, level)
                    for sid in sids
                    for level in self._service.list_building_levels(faction, sid)
                ),
                key=lambda item: (item.key.sid, item.key.level),
            )
        )

    def _show_discovery_error(self, exc: Exception) -> None:
        message = f"Request could not be completed: {exc}"
        self._view.show_error(message)
        self._set_status(message)
