from __future__ import annotations

from olden_db.comparison import PlanComparison
from olden_db.decision_summary import (
    DecisionSummary,
    PlansDifferObservation,
)
from olden_db.desktop.comparison_state import ComparisonState
from olden_db.desktop.presenters.comparison_presenter import ComparisonPresenter
from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan, GameDate


KEY = BuildingKey("undead", "Build_Tier_6", 1)
BUILDING = BuildingLevel(
    key=KEY,
    category="Dwelling",
    name_key=None,
    scene_slot=None,
    cost=ResourceCost(),
)
PLAN = BuildPlan(
    faction="undead",
    target=KEY,
    order_number=1,
    steps=(),
    total_cost=ResourceCost(),
    starting_date=GameDate(1, 1, 1),
)
COMPARISON = PlanComparison(
    left_plan=PLAN,
    right_plan=PLAN,
    action_delta=0,
    completion_date_delta=0,
    resource_delta=ResourceCost(),
    added_buildings=(),
    removed_buildings=(),
    identical=False,
)
SUMMARY = DecisionSummary(
    comparison=COMPARISON,
    observations=(PlansDifferObservation(),),
)


class Service:
    def __init__(self):
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
        return SUMMARY


class View:
    def __init__(self):
        self.compare_enabled = False
        self.comparison = None
        self.observations = None

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
        self.compare_enabled = enabled

    def clear_results(self):
        self.comparison = None
        self.observations = None

    def show_comparison(self, comparison):
        self.comparison = comparison

    def show_decision_summary(self, observations):
        self.observations = observations

    def show_error(self, message):
        raise RuntimeError(message)


def select(presenter, side):
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

    select(presenter, "left")
    if state.right.faction is not None:
        raise RuntimeError("Left selection modified right state")

    select(presenter, "right")
    if not view.compare_enabled:
        raise RuntimeError("Complete targets did not enable comparison")

    presenter.on_compare()
    if service.summary_calls != 1 or service.compare_calls != 0:
        raise RuntimeError(
            "Comparison workflow did not use one DecisionSummary retrieval"
        )
    if view.comparison is not SUMMARY.comparison:
        raise RuntimeError(
            "Raw comparison was not sourced from DecisionSummary.comparison"
        )
    if view.observations != ("The selected plans differ.",):
        raise RuntimeError("Decision summary was not displayed")

    presenter.on_level_changed("left", 1)
    if (
        state.current_comparison is not None
        or state.current_decision_summary is not None
        or view.comparison is not None
        or view.observations is not None
    ):
        raise RuntimeError("Selection change retained stale results")
    if state.right.level != 1:
        raise RuntimeError("Left change modified right state")

    print("Desktop comparison validation completed successfully.")
    print("Independent left and right state remained preserved.")
    print("One DecisionSummary retrieval powered both result panels.")
    print("No direct compare_plans retrieval occurred.")
    print("Selection changes cleared comparison and summary results.")


if __name__ == "__main__":
    main()
