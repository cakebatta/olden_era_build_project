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

from ..formatting import (
    format_diagnostic_summary,
    format_faction_status,
    format_game_date,
    format_resource_cost,
    format_step_count,
)
from ..planner_diagnostics import adapt_planner_diagnostics
from ..planning_summary import (
    DailyScheduleRowPresentation,
    PlanningSummaryPresentation,
)
from ..planning_timeline import BuildPlanTimelinePresentation, TimelineStepPresentation
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
        self._last_workspace_presentation: (
            PlanningWorkspacePresentation | None
        ) = None
        self._display_text_cache: dict[BuildingKey, str] = {}

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
        diagnostics = self._diagnostics_for(base)
        failure_message = (
            base.latest_failure.message
            if base.latest_failure is not None
            else None
        )
        selection = base.selection
        faction_text = selection.faction if selection is not None else self._state.selected_faction
        target_text = self._display_text(selection.target) if selection is not None else None
        starting_date_text = (
            format_game_date(selection.starting_date)
            if selection is not None
            else format_game_date(self._state.starting_date)
        )
        missing_inputs = self._missing_input_text()
        selection_summary = (
            missing_inputs
            if selection is None
            else f"{selection.faction} / {target_text} / starts {starting_date_text}"
        )
        retained = base.retains_previous_result
        summary = self._build_summary(
            base=base,
            result=result,
            diagnostics=diagnostics,
            faction_text=faction_text,
            target_text=target_text,
            starting_date_text=starting_date_text,
            failure_message=failure_message,
            missing_inputs=missing_inputs,
        )
        if base.execution_status is PlanningExecutionStatus.PENDING:
            heading = "Planning in progress"
            detail = (
                "Evaluating the current selection."
                if not retained
                else "Evaluating the current selection while retaining the Previous Accepted Plan."
            )
        elif base.execution_status is PlanningExecutionStatus.READY:
            heading = "Current plan ready"
            detail = f"Revision {base.selection_revision} is accepted."
        elif base.execution_status is PlanningExecutionStatus.FAILED:
            heading = "Current request failed"
            detail = (
                "The current selection could not be planned."
                if not retained
                else "The current selection failed. The displayed summary is the Previous Accepted Plan."
            )
        else:
            heading = "Planning selection incomplete"
            detail = missing_inputs
        presentation = PlanningWorkspacePresentation(
            execution_status=base.execution_status,
            status_heading=heading,
            status_detail=detail,
            selection_summary=selection_summary,
            summary=summary,
            failure_message=failure_message,
            diagnostics=diagnostics,
            selection_revision=base.selection_revision,
            result_revision=base.result_revision,
            timeline=self._build_timeline(base=base, result=result),
        )
        if base.result_is_current and result is not None:
            self._state.store_workspace_result(result.plan)
        else:
            self._state.clear_results()
        if presentation != self._last_workspace_presentation:
            self._view.render_workspace(presentation)
            self._last_workspace_presentation = presentation
        if base.execution_status is PlanningExecutionStatus.READY:
            self._set_status(f"Planning revision {base.selection_revision} completed.")
        elif base.execution_status is PlanningExecutionStatus.FAILED:
            self._set_status(
                "Current planning request failed"
                + (f": {failure_message}" if failure_message else ".")
            )

    def _diagnostics_for(self, base):
        result = base.accepted_result
        if (
            base.execution_status is PlanningExecutionStatus.FAILED
            and base.latest_failure is not None
        ):
            return adapt_planner_diagnostics(base.latest_failure.diagnostics)
        if result is not None:
            return adapt_planner_diagnostics(result.diagnostics)
        return ()

    def _display_text(self, key: BuildingKey) -> str:
        cached = self._display_text_cache.get(key)
        if cached is not None:
            return cached
        text = self._service.get_building_display_text(key)
        self._display_text_cache[key] = text
        return text

    def _missing_input_text(self) -> str:
        missing: list[str] = []
        if self._state.selected_faction is None:
            missing.append("faction")
        if self._state.selected_building_sid is None:
            missing.append("target building")
        if self._state.selected_level is None:
            missing.append("target level")
        return "Planning selection is complete." if not missing else "Missing: " + ", ".join(missing) + "."

    def _build_summary(
        self,
        *,
        base,
        result,
        diagnostics,
        faction_text,
        target_text,
        starting_date_text,
        failure_message,
        missing_inputs,
    ) -> PlanningSummaryPresentation:
        retained = base.retains_previous_result
        if result is None:
            return PlanningSummaryPresentation(
                lifecycle_status=base.execution_status.value,
                result_status=(
                    "Planning in progress"
                    if base.execution_status is PlanningExecutionStatus.PENDING
                    else "No accepted plan"
                ),
                faction_text=faction_text,
                target_text=target_text,
                starting_date_text=starting_date_text,
                displayed_result_target_text=None,
                step_count_text=None,
                completion_date_text=None,
                total_cost_text=None,
                daily_schedule_rows=(),
                diagnostic_summary=format_diagnostic_summary(diagnostics),
                failure_message=failure_message,
                missing_inputs_text=missing_inputs,
                is_retained_previous_result=False,
            )
        plan = result.plan
        rows = tuple(
            DailyScheduleRowPresentation(
                date_text=format_game_date(item.date),
                building_text=self._display_text(item.building),
                cost_text=format_resource_cost(item.cost),
            )
            for item in result.daily_construction_schedule
        )
        return PlanningSummaryPresentation(
            lifecycle_status=base.execution_status.value,
            result_status=("Previous Accepted Plan" if retained else "Current Accepted Plan"),
            faction_text=faction_text,
            target_text=target_text,
            starting_date_text=starting_date_text,
            displayed_result_target_text=self._display_text(plan.target),
            step_count_text=format_step_count(plan.build_actions),
            completion_date_text=format_game_date(plan.completion_date),
            total_cost_text=format_resource_cost(plan.total_cost),
            daily_schedule_rows=rows,
            diagnostic_summary=format_diagnostic_summary(diagnostics),
            failure_message=failure_message,
            missing_inputs_text=(missing_inputs if base.execution_status is PlanningExecutionStatus.EMPTY else None),
            is_retained_previous_result=retained,
        )

    def _build_timeline(
        self,
        *,
        base,
        result,
    ) -> BuildPlanTimelinePresentation:
        retained = base.retains_previous_result
        if result is None:
            return BuildPlanTimelinePresentation(
                result_status="No accepted plan",
                empty_state_text=self._timeline_empty_state(base),
                steps=(),
                is_retained_previous_result=False,
            )
        total_steps = len(result.plan.steps)
        steps = tuple(
            TimelineStepPresentation(
                step_number=step.step_number,
                position_text=f"Step {step.step_number} of {total_steps}",
                building_name=self._display_text(step.building),
                level_text=f"Level {step.building.level}",
                construction_date_text=format_game_date(step.date),
                individual_cost_text=format_resource_cost(step.individual_cost),
                cumulative_cost_text=format_resource_cost(step.cumulative_cost),
                completion_order_text=(
                    "Completes first"
                    if step.step_number == 1
                    else f"Completes {step.step_number}{self._ordinal_suffix(step.step_number)}"
                ),
            )
            for step in result.plan.steps
        )
        return BuildPlanTimelinePresentation(
            result_status=(
                "Previous Accepted Plan" if retained else "Current Accepted Plan"
            ),
            empty_state_text=(
                "No construction actions are required because the target is "
                "available at the active scenario start."
                if not steps
                else None
            ),
            steps=steps,
            is_retained_previous_result=retained,
        )

    @staticmethod
    def _timeline_empty_state(base) -> str:
        if base.execution_status is PlanningExecutionStatus.PENDING:
            return "Planning is in progress. No accepted timeline is available yet."
        if base.execution_status is PlanningExecutionStatus.FAILED:
            return "The current request failed before a plan was accepted."
        return "Complete the planning selection to view the build timeline."

    @staticmethod
    def _ordinal_suffix(number: int) -> str:
        if 10 <= number % 100 <= 20:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")

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
