from __future__ import annotations

from dataclasses import dataclass

from olden_db.desktop.economy_state import EconomyTimelineState
from olden_db.desktop.presenters.economy_presenter import (
    EconomyTimelinePresenter,
)
from olden_db.desktop.state import PlannerState
from olden_db.models import BuildingKey, ResourceCost
from olden_db.planner import BuildPlan, GameDate
from olden_db.scenario import PlanningScenario


DWELLING = BuildingKey("undead", "Build_Tier_1", 1)
TARGET = BuildingKey("undead", "Build_Tier_5", 1)
DAY_1 = GameDate(1, 1, 1)
DAY_2 = GameDate(1, 1, 2)


@dataclass(frozen=True)
class Family:
    base_sid: str = "skeleton"


@dataclass(frozen=True)
class StockEntry:
    date: GameDate
    dwelling: BuildingKey
    available: int
    unit_family: Family = Family()


@dataclass(frozen=True)
class Stock:
    entries: tuple[StockEntry, ...]


@dataclass(frozen=True)
class Ledger:
    plan: BuildPlan
    stock: Stock
    feasible: bool = True


PLAN = BuildPlan(
    faction="undead",
    target=TARGET,
    order_number=1,
    steps=(),
    total_cost=ResourceCost(),
    starting_date=DAY_1,
)
LEDGER = Ledger(
    plan=PLAN,
    stock=Stock(
        (
            StockEntry(DAY_1, DWELLING, 30),
            StockEntry(DAY_2, DWELLING, 30),
        )
    ),
)


class Service:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def generate_resource_ledger(
        self,
        faction,
        sid,
        level,
        actions,
        starting_resources,
        *,
        scenario,
    ):
        self.calls.append(
            (
                faction,
                sid,
                level,
                actions,
                starting_resources,
                scenario,
            )
        )
        return LEDGER


class View:
    def __init__(self) -> None:
        self.set_controls_count = 0
        self.apply_state_count = 0
        self.last_applied = None
        self.ledger = None
        self.error = ""

    def set_event_handlers(self, **handlers):
        self.handlers = handlers

    def set_planning_context(self, **context):
        pass

    def clear_planning_context(self):
        pass

    def clear_recruitment_controls(self):
        pass

    def set_generate_enabled(self, enabled):
        pass

    def show_input_error(self, message):
        self.error = message

    def clear_input_error(self):
        pass

    def show_recruitment_error(self, message):
        self.error = message

    def clear_recruitment_error(self):
        self.error = ""

    def clear_ledger(self):
        self.ledger = None

    def show_ledger(self, ledger):
        self.ledger = ledger

    def set_recruitment_controls(self, ledger, selections):
        self.set_controls_count += 1
        self.last_applied = selections

    def apply_recruitment_state(self, ledger, selections):
        self.apply_state_count += 1
        self.last_applied = selections

    def show_error(self, message):
        self.error = message


def main() -> None:
    service = Service()
    planner_state = PlannerState(
        selected_faction="undead",
        selected_building_sid="Build_Tier_5",
        selected_level=1,
        active_scenario=PlanningScenario(),
    )
    state = EconomyTimelineState(
        starting_resources=ResourceCost(gold=15000)
    )
    view = View()
    presenter = EconomyTimelinePresenter(
        service,
        planner_state,
        state,
        view,
        lambda message: None,
    )
    presenter.initialize()

    presenter.on_generate()
    if view.set_controls_count != 1:
        raise RuntimeError(
            "Explicit generation did not build recruitment controls once"
        )

    presenter.on_recruitment_changed(
        DAY_1,
        DWELLING,
        10,
        0,
    )
    if view.set_controls_count != 1:
        raise RuntimeError(
            "Accepted edit rebuilt the complete recruitment schedule"
        )
    if view.apply_state_count != 1:
        raise RuntimeError(
            "Accepted edit did not update controls in place"
        )
    if state.recruitment_selections[0].base_quantity != 10:
        raise RuntimeError(
            "Accepted slider/entry value was not preserved"
        )
    if state.current_ledger is not None:
        raise RuntimeError(
            "Accepted edit did not clear stale ledger output"
        )

    presenter.on_recruitment_changed(
        DAY_1,
        DWELLING,
        12,
        0,
    )
    if view.set_controls_count != 1:
        raise RuntimeError(
            "Repeated edit caused schedule flicker/reconstruction"
        )
    if state.recruitment_selections[0].base_quantity != 12:
        raise RuntimeError(
            "Repeated edit reset the accepted quantity"
        )

    presenter.on_recruitment_changed(
        DAY_2,
        DWELLING,
        19,
        0,
    )
    if len(state.recruitment_selections) != 1:
        raise RuntimeError(
            "Shared-stock over-allocation entered immutable state"
        )
    if "18 creatures remain available" not in view.error:
        raise RuntimeError(
            "Over-allocation did not report the authoritative limit"
        )
    if view.set_controls_count != 1:
        raise RuntimeError(
            "Rejected edit rebuilt the recruitment schedule"
        )

    presenter.on_generate()
    if view.set_controls_count != 2:
        raise RuntimeError(
            "Explicit regeneration did not rebuild controls exactly once"
        )
    if len(service.calls[-1][3]) != 1:
        raise RuntimeError(
            "Regeneration did not receive the preserved action"
        )
    if service.calls[-1][3][0].base_quantity != 12:
        raise RuntimeError(
            "Regeneration reset the scheduled quantity to zero"
        )
    if view.last_applied != state.recruitment_selections:
        raise RuntimeError(
            "Rebuilt controls did not receive immutable schedule state"
        )

    print("Desktop recruitment-edit validation completed successfully.")
    print("Accepted edits updated rows in place without rebuilding.")
    print("Slider and entry values remained in immutable schedule state.")
    print("Repeated edits did not flicker or reset recruitment controls.")
    print("Shared-stock rejection restored accepted values in place.")
    print("Only explicit regeneration rebuilt the recruitment schedule.")
    print("Regeneration preserved RecruitmentAction quantities.")


if __name__ == "__main__":
    main()
