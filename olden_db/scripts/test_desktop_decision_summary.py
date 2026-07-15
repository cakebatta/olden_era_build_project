from __future__ import annotations

from olden_db.comparison import PlanComparison
from olden_db.decision_summary import (
    ActionDeltaObservation,
    BuildingAddedObservation,
    BuildingRemovedObservation,
    CompletionDeltaObservation,
    DecisionSummary,
    PlansDifferObservation,
    PlansIdenticalObservation,
    ResourceDeltaObservation,
)
from olden_db.desktop.comparison_state import ComparisonState
from olden_db.desktop.presenters.comparison_presenter import ComparisonPresenter
from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan, GameDate


TARGET = BuildingKey("undead", "Build_Tier_6", 1)
WALL = BuildingKey("undead", "Build_Wall", 1)
MARKET = BuildingKey("undead", "Build_Marketplace", 1)
BUILDING = BuildingLevel(
    key=TARGET,
    category="Dwelling",
    name_key=None,
    scene_slot=None,
    cost=ResourceCost(),
)
PLAN = BuildPlan(
    faction="undead",
    target=TARGET,
    order_number=1,
    steps=(),
    total_cost=ResourceCost(),
    starting_date=GameDate(1, 1, 1),
)
COMPARISON = PlanComparison(
    left_plan=PLAN,
    right_plan=PLAN,
    action_delta=1,
    completion_date_delta=2,
    resource_delta=ResourceCost(gold=3500, wood=5, ore=5),
    added_buildings=(WALL,),
    removed_buildings=(MARKET,),
    identical=False,
)
OBSERVATIONS = (
    PlansDifferObservation(),
    ActionDeltaObservation(1),
    CompletionDeltaObservation(2),
    ResourceDeltaObservation("gold", 3500),
    ResourceDeltaObservation("wood", 5),
    ResourceDeltaObservation("ore", 5),
    BuildingAddedObservation(WALL),
    BuildingRemovedObservation(MARKET),
)
SUMMARY = DecisionSummary(
    comparison=COMPARISON,
    observations=OBSERVATIONS,
)
IDENTICAL_COMPARISON = PlanComparison(
    left_plan=PLAN,
    right_plan=PLAN,
    action_delta=0,
    completion_date_delta=0,
    resource_delta=ResourceCost(),
    added_buildings=(),
    removed_buildings=(),
    identical=True,
)
IDENTICAL_SUMMARY = DecisionSummary(
    comparison=IDENTICAL_COMPARISON,
    observations=(PlansIdenticalObservation(),),
)


class Service:
    def __init__(self):
        self.summary = SUMMARY
        self.summary_calls = 0
        self.compare_calls = 0

    def list_factions(self):
        return ("undead",)

    def list_buildings(self, faction):
        return ("Build_Tier_6",)

    def list_building_levels(self, faction, sid):
        return (1,)

    def get_building(self, faction, sid, level):
        return BUILDING

    def compare_plans(self, *args, **kwargs):
        self.compare_calls += 1
        raise RuntimeError(
            "ComparisonPresenter must not call compare_plans directly"
        )

    def generate_decision_summary(self, *args, **kwargs):
        self.summary_calls += 1
        return self.summary


class View:
    def __init__(self):
        self.observations = None
        self.comparison = None

    def set_event_handlers(self, **handlers):
        pass

    def set_factions(self, values):
        pass

    def set_buildings(self, side, values):
        pass

    def set_levels(self, side, values):
        pass

    def set_scenario_candidates(self, side, buildings, scenario):
        pass

    def set_mode(self, side, count):
        pass

    def set_compare_enabled(self, enabled):
        pass

    def clear_results(self):
        self.observations = None
        self.comparison = None

    def show_comparison(self, comparison):
        self.comparison = comparison

    def show_decision_summary(self, observations):
        self.observations = observations

    def show_error(self, message):
        raise RuntimeError(message)


def select_both(presenter):
    for side in ("left", "right"):
        presenter.on_faction_changed(side, "undead")
        presenter.on_building_changed(side, "Build_Tier_6")
        presenter.on_level_changed(side, 1)


def main():
    service = Service()
    state = ComparisonState()
    view = View()
    presenter = ComparisonPresenter(
        service,
        state,
        view,
        lambda message: None,
    )
    presenter.initialize()
    select_both(presenter)
    presenter.on_compare()

    expected = (
        "The selected plans differ.",
        "The right plan requires 1 additional construction action.",
        "The right plan finishes 2 days later.",
        "Gold changes by +3500.",
        "Wood changes by +5.",
        "Ore changes by +5.",
        "Construction added: Build_Wall level 1.",
        "Construction removed: Build_Marketplace level 1.",
    )
    if view.observations != expected:
        raise RuntimeError(
            "Observation mapping or backend ordering was not preserved"
        )
    if service.summary_calls != 1:
        raise RuntimeError(
            "One Compare action must make exactly one summary retrieval"
        )
    if service.compare_calls != 0:
        raise RuntimeError(
            "Presenter performed a duplicate direct comparison retrieval"
        )
    if state.current_decision_summary is not SUMMARY:
        raise RuntimeError("DecisionSummary was not retained in state")
    if state.current_comparison is not SUMMARY.comparison:
        raise RuntimeError(
            "PlanComparison was not sourced from DecisionSummary.comparison"
        )
    if view.comparison is not SUMMARY.comparison:
        raise RuntimeError(
            "Comparison panel did not use DecisionSummary.comparison"
        )

    right_scenario_before = state.right.scenario
    presenter.on_level_changed("left", 1)
    if (
        state.current_decision_summary is not None
        or state.current_comparison is not None
    ):
        raise RuntimeError("Selection change retained stale results")
    if state.right.scenario is not right_scenario_before:
        raise RuntimeError("Left change altered right scenario")

    service.summary = IDENTICAL_SUMMARY
    presenter.on_compare()
    if view.comparison is not IDENTICAL_SUMMARY.comparison:
        raise RuntimeError(
            "Identical comparison did not come from the returned summary"
        )
    if view.observations != ("The selected plans are identical.",):
        raise RuntimeError(
            "Identical summary contained extra or incorrect observations"
        )
    if service.summary_calls != 2 or service.compare_calls != 0:
        raise RuntimeError(
            "Repeated Compare actions did not preserve the one-call boundary"
        )

    print("Desktop decision-summary validation completed successfully.")
    print("Each Compare action made exactly one backend retrieval.")
    print("compare_plans was never called directly by the presenter.")
    print("DecisionSummary.comparison was the sole comparison source.")
    print("Backend observation ordering and presentation remained unchanged.")
    print("Selection changes cleared stale comparison and summary results.")


if __name__ == "__main__":
    main()
