from __future__ import annotations

from olden_db.decision_summary import (
    ActionDeltaObservation,
    BuildingAddedObservation,
    BuildingRemovedObservation,
    CompletionDeltaObservation,
    DecisionObservation,
    PlansDifferObservation,
    PlansIdenticalObservation,
    ResourceDeltaObservation,
)
from olden_db.models import BuildingKey
from olden_db.query import QueryError
from olden_db.scenario import (
    PlanningScenario,
    ScenarioError,
    StartingBuildingOverride,
)

from ..comparison_state import ComparisonState


class ComparisonPresenter:
    """Orchestrate comparison through the DecisionSummary Query Layer pipeline."""

    def __init__(self, service, state: ComparisonState, view, set_status) -> None:
        self.s = service
        self.state = state
        self.v = view
        self.status = set_status

    def initialize(self) -> None:
        self.v.set_event_handlers(
            on_faction_changed=self.on_faction_changed,
            on_building_changed=self.on_building_changed,
            on_level_changed=self.on_level_changed,
            on_scenario_changed=self.on_scenario_changed,
            on_reset_scenario=self.on_reset_scenario,
            on_compare=self.on_compare,
        )
        self.v.set_factions(self.s.list_factions())
        self.v.set_mode("left", 0)
        self.v.set_mode("right", 0)
        self.v.set_compare_enabled(False)
        self.v.clear_results()

    def side(self, name):
        return self.state.left if name == "left" else self.state.right

    def on_faction_changed(self, name, faction) -> None:
        try:
            sids = self.s.list_buildings(faction)
            candidates = tuple(
                sorted(
                    (
                        self.s.get_building(faction, sid, level)
                        for sid in sids
                        for level in self.s.list_building_levels(faction, sid)
                    ),
                    key=lambda building: (
                        building.key.sid,
                        building.key.level,
                    ),
                )
            )
        except QueryError as exc:
            self._error(exc)
            return

        side = self.side(name)
        side.select_faction(faction, candidates)
        self.v.set_buildings(name, sids)
        self.v.set_scenario_candidates(name, candidates, side.scenario)
        self.v.set_mode(name, 0)
        self._changed()

    def on_building_changed(self, name, sid) -> None:
        side = self.side(name)
        if side.faction is None:
            return
        try:
            levels = self.s.list_building_levels(side.faction, sid)
        except QueryError as exc:
            self._error(exc)
            return
        side.select_building(sid)
        self.v.set_levels(name, levels)
        self._changed()

    def on_level_changed(self, name, level) -> None:
        self.side(name).select_level(level)
        self._changed()

    def on_scenario_changed(
        self,
        name,
        key: BuildingKey,
        available,
    ) -> None:
        side = self.side(name)
        building = next(
            (
                candidate
                for candidate in side.scenario_candidates
                if candidate.key == key
            ),
            None,
        )
        if building is None:
            self.status("Unknown comparison scenario building.")
            return

        overrides = {
            override.building: override.available_at_start
            for override in side.scenario.starting_building_overrides
        }
        if available == building.constructed_on_start:
            overrides.pop(key, None)
        else:
            overrides[key] = available

        try:
            scenario = PlanningScenario(
                tuple(
                    StartingBuildingOverride(building_key, value)
                    for building_key, value in overrides.items()
                )
            )
        except ScenarioError as exc:
            self._error(exc)
            return

        side.scenario = scenario
        self.v.set_scenario_candidates(
            name,
            side.scenario_candidates,
            scenario,
        )
        self.v.set_mode(name, len(scenario.starting_building_overrides))
        self._changed()

    def on_reset_scenario(self, name) -> None:
        side = self.side(name)
        side.scenario = PlanningScenario()
        self.v.set_scenario_candidates(
            name,
            side.scenario_candidates,
            side.scenario,
        )
        self.v.set_mode(name, 0)
        self._changed()

    def on_compare(self) -> None:
        if not self.state.can_compare:
            self.status("Complete both comparison targets first.")
            return

        left = self.state.left
        right = self.state.right

        try:
            summary = self.s.generate_decision_summary(
                left.faction,
                left.building_sid,
                left.level,
                right_faction=right.faction,
                right_sid=right.building_sid,
                right_level=right.level,
                left_scenario=left.scenario,
                right_scenario=right.scenario,
            )
        except (QueryError, ScenarioError) as exc:
            self._error(exc)
            return

        comparison = summary.comparison
        self.state.current_decision_summary = summary
        self.state.current_comparison = comparison
        self.v.show_comparison(comparison)
        self.v.show_decision_summary(
            tuple(
                self._format_observation(observation)
                for observation in summary.observations
            )
        )
        self.status("Plan comparison and decision summary generated successfully.")

    def _format_observation(
        self,
        observation: DecisionObservation,
    ) -> str:
        if isinstance(observation, PlansIdenticalObservation):
            return "The selected plans are identical."

        if isinstance(observation, PlansDifferObservation):
            return "The selected plans differ."

        if isinstance(observation, ActionDeltaObservation):
            amount = abs(observation.delta_actions)
            noun = "construction action" if amount == 1 else "construction actions"
            if observation.delta_actions > 0:
                return f"The right plan requires {amount} additional {noun}."
            return f"The right plan requires {amount} fewer {noun}."

        if isinstance(observation, CompletionDeltaObservation):
            amount = abs(observation.delta_days)
            noun = "day" if amount == 1 else "days"
            if observation.delta_days > 0:
                return f"The right plan finishes {amount} {noun} later."
            return f"The right plan finishes {amount} {noun} earlier."

        if isinstance(observation, ResourceDeltaObservation):
            sign = "+" if observation.delta > 0 else ""
            return (
                f"{observation.resource.capitalize()} changes by "
                f"{sign}{observation.delta}."
            )

        if isinstance(observation, BuildingAddedObservation):
            return (
                "Construction added: "
                f"{observation.building.sid} level "
                f"{observation.building.level}."
            )

        if isinstance(observation, BuildingRemovedObservation):
            return (
                "Construction removed: "
                f"{observation.building.sid} level "
                f"{observation.building.level}."
            )

        raise TypeError(
            f"Unsupported decision observation: {type(observation).__name__}"
        )

    def _changed(self) -> None:
        self.state.clear_result()
        self.v.clear_results()
        self.v.set_compare_enabled(self.state.can_compare)

    def _error(self, exc) -> None:
        self.state.clear_result()
        message = f"Comparison could not be completed: {exc}"
        self.v.show_error(message)
        self.status(message)
