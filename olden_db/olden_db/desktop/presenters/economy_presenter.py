from __future__ import annotations

from collections.abc import Callable

from olden_db.constants import RESOURCE_NAMES
from olden_db.models import BuildingKey, ResourceCost
from olden_db.planner import GameDate
from olden_db.query import PlanningQueryService, QueryError

from ..economy_state import EconomyTimelineState, RecruitmentSelection
from ..state import PlannerState


class EconomyTimelinePresenter:
    """Coordinate immutable user input and one authoritative ledger request."""

    def __init__(
        self,
        service: PlanningQueryService,
        planner_state: PlannerState,
        state: EconomyTimelineState,
        view,
        set_status: Callable[[str], None],
    ) -> None:
        self._service = service
        self._planner_state = planner_state
        self._state = state
        self._view = view
        self._set_status = set_status

    def initialize(self) -> None:
        self._view.set_event_handlers(
            on_resources_changed=self.on_starting_resources_changed,
            on_recruitment_changed=self.on_recruitment_changed,
            on_generate=self.on_generate,
        )
        self.refresh_context()

    def refresh_context(self) -> None:
        self._state.clear_ledger()
        self._view.clear_ledger()
        if not self._planner_state.has_complete_target:
            self._state.clear_recruitment()
            self._view.clear_planning_context()
            self._view.clear_recruitment_controls()
            self._view.set_generate_enabled(False)
            return

        faction = self._planner_state.selected_faction
        sid = self._planner_state.selected_building_sid
        level = self._planner_state.selected_level
        assert faction is not None
        assert sid is not None
        assert level is not None
        self._view.set_planning_context(
            faction=faction,
            sid=sid,
            level=level,
            override_count=self._planner_state.override_count,
        )
        self._update_generate_enabled()

    def on_planning_context_changed(self) -> None:
        self._state.clear_recruitment()
        self.refresh_context()

    def on_starting_resources_changed(
        self,
        values: dict[str, str],
    ) -> None:
        try:
            parsed = {
                name: int(values.get(name, ""))
                for name in RESOURCE_NAMES
            }
        except ValueError:
            self._state.invalidate_starting_resources()
            self._view.clear_ledger()
            self._view.show_input_error(
                "Starting resources must be whole numbers."
            )
            self._update_generate_enabled()
            return

        if any(value < 0 for value in parsed.values()):
            self._state.invalidate_starting_resources()
            self._view.clear_ledger()
            self._view.show_input_error(
                "Starting resources cannot be negative."
            )
            self._update_generate_enabled()
            return

        self._state.replace_starting_resources(ResourceCost(**parsed))
        self._view.clear_input_error()
        self._view.clear_ledger()
        self._update_generate_enabled()

    def on_recruitment_changed(
        self,
        date: GameDate,
        dwelling: BuildingKey,
        base_quantity: int,
        upgraded_quantity: int,
    ) -> None:
        if base_quantity < 0 or upgraded_quantity < 0:
            self._view.show_recruitment_error(
                "Recruitment quantities cannot be negative."
            )
            self._view.apply_recruitment_state(
                self._state.recruitment_selections
            )
            return

        selection = RecruitmentSelection(
            date=date,
            dwelling=dwelling,
            base_quantity=base_quantity,
            upgraded_quantity=upgraded_quantity,
        )
        self._state.replace_recruitment_selection(selection)
        self._view.clear_recruitment_error()
        self._view.clear_ledger()
        self._view.apply_recruitment_state(
            self._state.recruitment_selections
        )

    def on_generate(self) -> None:
        if (
            not self._planner_state.has_complete_target
            or not self._state.starting_resources_valid
        ):
            self._update_generate_enabled()
            self._set_status(
                "Complete a target and enter valid starting resources first."
            )
            return

        faction = self._planner_state.selected_faction
        sid = self._planner_state.selected_building_sid
        level = self._planner_state.selected_level
        assert faction is not None
        assert sid is not None
        assert level is not None

        try:
            ledger = self._service.generate_resource_ledger(
                faction,
                sid,
                level,
                self._state.recruitment_actions,
                self._state.starting_resources,
                scenario=self._planner_state.active_scenario,
            )
        except (QueryError, ValueError) as exc:
            self._state.clear_ledger()
            message = f"Economy timeline could not be generated: {exc}"
            self._view.show_error(message)
            self._view.show_recruitment_error(str(exc))
            self._view.apply_recruitment_state(
                self._state.recruitment_selections
            )
            self._set_status(message)
            return

        self._state.current_ledger = ledger
        self._state.control_ledger = ledger
        self._view.show_ledger(ledger)
        self._view.set_recruitment_controls(
            ledger,
            self._state.recruitment_selections,
        )
        self._set_status(
            "Economy timeline generated successfully: "
            f"{'feasible' if ledger.feasible else 'first deficit displayed'}."
        )

    def _update_generate_enabled(self) -> None:
        self._view.set_generate_enabled(
            self._planner_state.has_complete_target
            and self._state.starting_resources_valid
        )
