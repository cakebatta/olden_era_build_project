from __future__ import annotations

from olden_db.query import QueryError

from .economy_state import RecruitmentSelection
from .presenters.economy_presenter import EconomyTimelinePresenter
from .presenters.planner_presenter import PlannerPresenter, SCENARIO_ERRORS


class ScenarioAwarePlannerPresenter(PlannerPresenter):
    def __init__(
        self,
        *args,
        on_persisted_change=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._on_persisted_change = (
            on_persisted_change or (lambda: None)
        )

    def set_persisted_change_handler(self, handler):
        self._on_persisted_change = handler

    def available_factions(self):
        return self._service.list_factions()

    def available_buildings(self, faction):
        return self._service.list_buildings(faction)

    def available_levels(self, faction, sid):
        return self._service.list_building_levels(faction, sid)

    def apply_document(self, document):
        self.on_faction_changed(document.faction)
        self.on_building_changed(document.target.sid)
        self.on_level_changed(document.target.level)
        self._state.starting_date = document.starting_date
        self._state.replace_scenario(document.planning_scenario)
        self._view.set_starting_buildings(
            self._state.scenario_candidates,
            document.planning_scenario,
        )
        self._view.set_planning_mode(
            self._state.override_count
        )
        self._view._faction_var.set(document.faction)
        self._view._building_var.set(document.target.sid)
        self._view._level_var.set(
            str(document.target.level)
        )

    def on_faction_changed(self, faction):
        super().on_faction_changed(faction)
        self._on_persisted_change()

    def on_building_changed(self, sid):
        super().on_building_changed(sid)
        self._on_persisted_change()

    def on_level_changed(self, level):
        super().on_level_changed(level)
        self._on_persisted_change()

    def on_starting_building_changed(
        self,
        key,
        available,
    ):
        super().on_starting_building_changed(
            key,
            available,
        )
        self._on_persisted_change()

    def on_reset_scenario(self):
        super().on_reset_scenario()
        self._on_persisted_change()

    def on_generate_plan(self):
        if not self._state.has_complete_target:
            return

        faction = self._state.selected_faction
        sid = self._state.selected_building_sid
        level = self._state.selected_level
        self._clear_generated_results()
        scenario = self._state.active_scenario

        try:
            building = self._service.get_building(
                faction,
                sid,
                level,
            )
            statuses = (
                self._service.get_prerequisite_statuses(
                    faction,
                    sid,
                    level,
                    scenario=scenario,
                )
            )
            plan = self._service.generate_build_plan(
                faction,
                sid,
                level,
                starting_date=self._state.starting_date,
                scenario=scenario,
            )
            cost = plan.total_cost
            orders = self._service.enumerate_build_orders(
                faction,
                sid,
                level,
                scenario=scenario,
            )
        except (QueryError, *SCENARIO_ERRORS) as exc:
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


class ScenarioAwareEconomyPresenter(
    EconomyTimelinePresenter
):
    def __init__(
        self,
        *args,
        on_persisted_change=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._on_persisted_change = (
            on_persisted_change or (lambda: None)
        )

    def set_persisted_change_handler(self, handler):
        self._on_persisted_change = handler

    def apply_document(self, document):
        self._state.replace_starting_resources(
            document.starting_resources
        )
        self._state.recruitment_selections = tuple(
            RecruitmentSelection(
                date=action.date,
                dwelling=action.dwelling,
                base_quantity=action.base_quantity,
                upgraded_quantity=(
                    action.upgraded_quantity
                ),
            )
            for action in document.recruitment_actions
        )
        self._state.clear_recruitment_issue()
        for name, variable in (
            self._view._resource_vars.items()
        ):
            variable.set(
                str(
                    getattr(
                        document.starting_resources,
                        name,
                    )
                )
            )
        self._view.apply_recruitment_state(
            self._state.recruitment_selections
        )
        self.refresh_context()

    def on_starting_resources_changed(self, values):
        try:
            parsed = {
                name: int(value)
                for name, value in values.items()
            }
        except (TypeError, ValueError):
            self._state.invalidate_starting_resources(
                "Starting resources must be whole numbers."
            )
        else:
            if any(value < 0 for value in parsed.values()):
                self._state.invalidate_starting_resources(
                    "Starting resources cannot be negative."
                )

        super().on_starting_resources_changed(values)
        self._on_persisted_change()

    def on_recruitment_changed(
        self,
        date,
        dwelling,
        base_quantity,
        upgraded_quantity,
    ):
        if (
            base_quantity < 0
            or upgraded_quantity < 0
        ):
            self._state.mark_recruitment_invalid(
                "Recruitment quantities cannot be negative."
            )
        else:
            self._state.clear_recruitment_issue()

        super().on_recruitment_changed(
            date,
            dwelling,
            base_quantity,
            upgraded_quantity,
        )
        self._on_persisted_change()

    def on_generate(self):
        if (
            not self._planner_state.has_complete_target
            or not self._state.starting_resources_valid
        ):
            self._update_generate_enabled()
            self._set_status(
                "Complete a target and enter valid "
                "starting resources first."
            )
            return

        faction = self._planner_state.selected_faction
        sid = self._planner_state.selected_building_sid
        level = self._planner_state.selected_level

        try:
            ledger = (
                self._service.generate_resource_ledger(
                    faction,
                    sid,
                    level,
                    self._state.recruitment_actions,
                    self._state.starting_resources,
                    starting_date=(
                        self._planner_state.starting_date
                    ),
                    scenario=(
                        self._planner_state.active_scenario
                    ),
                )
            )
        except (QueryError, ValueError) as exc:
            self._state.clear_ledger()
            message = (
                "Economy timeline could not be "
                f"generated: {exc}"
            )
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
