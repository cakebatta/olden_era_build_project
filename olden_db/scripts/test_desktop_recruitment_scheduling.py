from __future__ import annotations

from dataclasses import dataclass
import inspect

from olden_db.desktop.economy_state import EconomyTimelineState
from olden_db.desktop.presenters.economy_presenter import (
    EconomyTimelinePresenter,
)
from olden_db.desktop.state import PlannerState
from olden_db.models import BuildingKey, ResourceCost
from olden_db.planner import BuildPlan, GameDate
from olden_db.query import QueryError
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
        self.reject = False

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
        if self.reject:
            raise QueryError(
                "requested recruitment exceeds authoritative stock"
            )
        return LEDGER


class View:
    def __init__(self) -> None:
        self.controls_built = 0
        self.applied = None
        self.ledger = None
        self.error = ""
        self.enabled = False

    def set_event_handlers(self, **handlers):
        self.handlers = handlers

    def set_planning_context(self, **context):
        pass

    def clear_planning_context(self):
        pass

    def clear_recruitment_controls(self):
        pass

    def set_generate_enabled(self, enabled):
        self.enabled = enabled

    def show_input_error(self, message):
        self.error = message

    def clear_input_error(self):
        self.error = ""

    def show_recruitment_error(self, message):
        self.error = message

    def clear_recruitment_error(self):
        self.error = ""

    def clear_ledger(self):
        self.ledger = None

    def show_ledger(self, ledger):
        self.ledger = ledger

    def set_recruitment_controls(self, ledger, selections):
        self.controls_built += 1
        self.applied = selections

    def apply_recruitment_state(self, selections):
        self.applied = selections

    def show_error(self, message):
        self.error = message


def main() -> None:
    presenter_source = inspect.getsource(EconomyTimelinePresenter)
    forbidden_fragments = (
        "stock.entries",
        "prior_purchases",
        "maximum_for_date",
        "remaining stock",
        "available -",
        "day_index <",
    )
    found = tuple(
        fragment
        for fragment in forbidden_fragments
        if fragment in presenter_source
    )
    if found:
        raise RuntimeError(
            "Desktop presenter contains forbidden stock semantics: "
            f"{found!r}"
        )

    service = Service()
    planner_state = PlannerState(
        selected_faction="undead",
        selected_building_sid="Build_Tier_5",
        selected_level=1,
        active_scenario=PlanningScenario(),
    )
    scenario_before = planner_state.active_scenario
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

    if len(service.calls) != 1:
        raise RuntimeError(
            "Initial timeline did not make exactly one ledger request"
        )

    presenter.on_recruitment_changed(
        DAY_1,
        DWELLING,
        30,
        0,
    )
    presenter.on_recruitment_changed(
        DAY_2,
        DWELLING,
        30,
        0,
    )

    if len(state.recruitment_selections) != 2:
        raise RuntimeError(
            "Desktop rejected a syntactically valid schedule"
        )
    if state.current_ledger is not None:
        raise RuntimeError(
            "Recruitment edit did not clear stale ledger state"
        )
    if view.applied != state.recruitment_selections:
        raise RuntimeError(
            "Smooth editing did not preserve immutable selections"
        )

    actions = state.recruitment_actions
    if len(actions) != 2:
        raise RuntimeError(
            "Immutable RecruitmentAction tuple was not constructed"
        )
    if (
        actions[0].base_quantity,
        actions[1].base_quantity,
    ) != (30, 30):
        raise RuntimeError(
            "User-requested quantities were silently altered"
        )

    service.reject = True
    presenter.on_generate()

    if len(service.calls) != 2:
        raise RuntimeError(
            "Generation did not use exactly one additional ledger request"
        )
    if service.calls[-1][3] != actions:
        raise RuntimeError(
            "Backend did not receive the exact immutable schedule"
        )
    if len(state.recruitment_selections) != 2:
        raise RuntimeError(
            "Backend rejection discarded the user's schedule"
        )
    if state.current_ledger is not None:
        raise RuntimeError(
            "Backend rejection retained a stale ledger"
        )
    if view.applied != state.recruitment_selections:
        raise RuntimeError(
            "Backend rejection did not preserve editable controls"
        )
    if "authoritative stock" not in view.error:
        raise RuntimeError(
            "Factual backend validation error was not displayed"
        )

    presenter.on_recruitment_changed(
        DAY_2,
        DWELLING,
        -1,
        0,
    )
    if len(state.recruitment_selections) != 2:
        raise RuntimeError(
            "Negative input changed the accepted schedule"
        )
    if "cannot be negative" not in view.error:
        raise RuntimeError(
            "Negative quantity was not rejected syntactically"
        )

    if (
        planner_state.selected_faction,
        planner_state.selected_building_sid,
        planner_state.selected_level,
        planner_state.active_scenario,
    ) != (
        "undead",
        "Build_Tier_5",
        1,
        scenario_before,
    ):
        raise RuntimeError(
            "Recruitment workflow modified planner or scenario state"
        )

    print("Desktop recruitment-boundary validation completed successfully.")
    print("Presenter source contains no stock-consumption calculations.")
    print("UI validation is limited to non-negative integer quantities.")
    print("Syntactically valid overstock requests remain user-controlled.")
    print("One generate_resource_ledger call remains authoritative.")
    print("Backend rejection preserves the immutable recruitment schedule.")
    print("Stale ledger state clears without altering planner state.")


if __name__ == "__main__":
    main()
