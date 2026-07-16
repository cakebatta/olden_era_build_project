from __future__ import annotations

from dataclasses import dataclass

from olden_db.desktop.economy_formatting import format_resource_ledger
from olden_db.desktop.economy_state import EconomyTimelineState
from olden_db.desktop.presenters.economy_presenter import (
    EconomyTimelinePresenter,
)
from olden_db.desktop.state import PlannerState
from olden_db.models import BuildingKey, ResourceCost
from olden_db.planner import GameDate
from olden_db.scenario import (
    PlanningScenario,
    StartingBuildingOverride,
)


TARGET = BuildingKey("undead", "Build_Tier_6", 1)
WALL = BuildingKey("undead", "Build_Wall", 1)


@dataclass(frozen=True)
class ConstructionEntry:
    date: GameDate
    building: BuildingKey
    cost: ResourceCost
    balance_after: ResourceCost


@dataclass(frozen=True)
class DailyBalance:
    date: GameDate
    balance: ResourceCost


@dataclass(frozen=True)
class Deficit:
    date: GameDate
    resource: str
    balance: int
    entry_index: int


@dataclass(frozen=True)
class Ledger:
    construction_entries: tuple[ConstructionEntry, ...]
    recruitment_entries: tuple[object, ...]
    daily_balances: tuple[DailyBalance, ...]
    construction_total: ResourceCost
    recruitment_total: ResourceCost
    combined_total: ResourceCost
    ending_balance: ResourceCost
    feasible: bool
    first_deficit: Deficit | None


FEASIBLE_LEDGER = Ledger(
    construction_entries=(
        ConstructionEntry(
            GameDate(1, 1, 1),
            TARGET,
            ResourceCost(gold=9000),
            ResourceCost(gold=1000),
        ),
    ),
    recruitment_entries=(),
    daily_balances=(
        DailyBalance(GameDate(1, 1, 1), ResourceCost(gold=1000)),
        DailyBalance(GameDate(1, 1, 2), ResourceCost(gold=1000)),
    ),
    construction_total=ResourceCost(gold=9000),
    recruitment_total=ResourceCost(),
    combined_total=ResourceCost(gold=9000),
    ending_balance=ResourceCost(gold=1000),
    feasible=True,
    first_deficit=None,
)

DEFICIT_LEDGER = Ledger(
    construction_entries=(
        ConstructionEntry(
            GameDate(1, 1, 1),
            TARGET,
            ResourceCost(gold=9000),
            ResourceCost(gold=-4000),
        ),
    ),
    recruitment_entries=(),
    daily_balances=(
        DailyBalance(GameDate(1, 1, 1), ResourceCost(gold=-4000)),
    ),
    construction_total=ResourceCost(gold=9000),
    recruitment_total=ResourceCost(),
    combined_total=ResourceCost(gold=9000),
    ending_balance=ResourceCost(gold=-4000),
    feasible=False,
    first_deficit=Deficit(
        GameDate(1, 1, 1),
        "gold",
        -4000,
        1,
    ),
)


class Service:
    def __init__(self):
        self.ledger = FEASIBLE_LEDGER
        self.calls = []
        self.plan_calls = 0
        self.stock_calls = 0

    def generate_resource_ledger(
        self,
        faction,
        sid,
        level,
        recruitment_actions,
        starting_resources,
        *,
        scenario,
    ):
        self.calls.append(
            (
                faction,
                sid,
                level,
                recruitment_actions,
                starting_resources,
                scenario,
            )
        )
        return self.ledger

    def generate_build_plan(self, *args, **kwargs):
        self.plan_calls += 1
        raise RuntimeError("Economy presenter must not request a plan")

    def generate_recruitment_stock(self, *args, **kwargs):
        self.stock_calls += 1
        raise RuntimeError("Economy presenter must not request stock")


class View:
    def __init__(self):
        self.generate_enabled = False
        self.ledger = None
        self.error = ""
        self.context = None

    def set_event_handlers(self, **handlers):
        self.handlers = handlers

    def set_planning_context(self, **context):
        self.context = context

    def clear_planning_context(self):
        self.context = None

    def set_generate_enabled(self, enabled):
        self.generate_enabled = enabled

    def show_input_error(self, message):
        self.error = message

    def clear_input_error(self):
        self.error = ""

    def clear_ledger(self):
        self.ledger = None

    def show_ledger(self, ledger):
        self.ledger = ledger

    def show_error(self, message):
        self.error = message


def complete_planner_state():
    return PlannerState(
        selected_faction="undead",
        selected_building_sid="Build_Tier_6",
        selected_level=1,
    )


def main():
    service = Service()
    planner_state = complete_planner_state()
    economy_state = EconomyTimelineState()
    view = View()
    messages = []

    presenter = EconomyTimelinePresenter(
        service,
        planner_state,
        economy_state,
        view,
        messages.append,
    )
    presenter.initialize()

    if economy_state.starting_resources != ResourceCost():
        raise RuntimeError("Starting resources did not default to zero")
    if not view.generate_enabled:
        raise RuntimeError("Complete planner target did not enable ledger")

    values = {
        "gold": "10000",
        "wood": "5",
        "ore": "4",
        "gemstones": "3",
        "crystals": "2",
        "mercury": "1",
        "dust": "0",
        "graal": "0",
    }
    presenter.on_starting_resources_changed(values)
    expected_resources = ResourceCost(
        gold=10000,
        wood=5,
        ore=4,
        gemstones=3,
        crystals=2,
        mercury=1,
    )
    if economy_state.starting_resources != expected_resources:
        raise RuntimeError("Immutable starting-resource state was incorrect")

    target_snapshot = (
        planner_state.selected_faction,
        planner_state.selected_building_sid,
        planner_state.selected_level,
    )
    presenter.on_generate()

    if len(service.calls) != 1:
        raise RuntimeError("Ledger generation was not exactly one call")
    call = service.calls[0]
    if call[3] != ():
        raise RuntimeError("Recruitment actions were not an empty tuple")
    if call[4] != expected_resources:
        raise RuntimeError("Starting resources were not passed unchanged")
    if call[5] is not planner_state.active_scenario:
        raise RuntimeError("Canonical scenario instance was not reused")
    if service.plan_calls or service.stock_calls:
        raise RuntimeError("Separate plan or stock retrieval occurred")
    if view.ledger is not FEASIBLE_LEDGER:
        raise RuntimeError("Authoritative ledger was not displayed")

    formatted = format_resource_ledger(FEASIBLE_LEDGER)
    if formatted.index("Day 1") > formatted.index("Day 2"):
        raise RuntimeError("Timeline dates were not in ledger order")
    if "Week boundary" not in formatted:
        raise RuntimeError("Week boundary was not marked")
    if "Total recruitment cost: gold: 0" not in formatted:
        raise RuntimeError("Zero recruitment total was not separated")
    if "Feasible: Yes" not in formatted:
        raise RuntimeError("Feasibility was not displayed")

    service.ledger = DEFICIT_LEDGER
    presenter.on_generate()
    deficit_text = format_resource_ledger(DEFICIT_LEDGER)
    required = (
        "First Deficit",
        "Resource: gold",
        "Signed balance: -4000",
        "Deficit magnitude: 4000",
        "Triggering entry: Construction",
    )
    if any(text not in deficit_text for text in required):
        raise RuntimeError("First-deficit presentation was incomplete")

    custom = PlanningScenario(
        (StartingBuildingOverride(WALL, False),)
    )
    planner_state.active_scenario = custom
    presenter.on_planning_context_changed()
    if economy_state.current_ledger is not None:
        raise RuntimeError("Scenario change retained a stale ledger")
    presenter.on_generate()
    if service.calls[-1][5] is not custom:
        raise RuntimeError("Custom scenario was not passed unchanged")

    presenter.on_starting_resources_changed(
        {**values, "gold": "-1"}
    )
    if economy_state.starting_resources_valid:
        raise RuntimeError("Negative starting resources were accepted")
    if view.generate_enabled:
        raise RuntimeError("Invalid input left generation enabled")

    presenter.on_starting_resources_changed(
        {**values, "gold": "not-a-number"}
    )
    if "whole numbers" not in view.error:
        raise RuntimeError("Invalid numeric input was not explained")

    if target_snapshot != (
        planner_state.selected_faction,
        planner_state.selected_building_sid,
        planner_state.selected_level,
    ):
        raise RuntimeError("Economy workflow modified planner target state")

    print("Desktop economy-timeline validation completed successfully.")
    print("Starting resources were retained as one immutable ResourceCost.")
    print("One generate_resource_ledger call used an empty recruitment tuple.")
    print("No separate plan or stock retrieval occurred.")
    print("Canonical and custom scenarios were passed unchanged.")
    print("Timeline ordering, week boundaries, and separated totals displayed.")
    print("Feasibility and first-deficit facts displayed without recommendations.")
    print("Target, scenario, and resource changes cleared stale ledger state.")
    print("Existing planner target state remained preserved.")


if __name__ == "__main__":
    main()
