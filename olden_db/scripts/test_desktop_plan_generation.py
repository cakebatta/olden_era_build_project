from __future__ import annotations

from collections.abc import Callable

from olden_db.desktop.formatting import (
    format_build_plan,
    format_prerequisites,
    format_resource_cost,
)
from olden_db.desktop.presenters.planner_presenter import PlannerPresenter
from olden_db.desktop.state import PlannerState
from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan, BuildStep, GameDate
from olden_db.query import QueryError


TARGET_KEY = BuildingKey("nature", "Build_Tier_4", 2)
PRE_KEY = BuildingKey("nature", "Build_Hall", 1)
START_KEY = BuildingKey("nature", "Build_Start", 1)

TARGET = BuildingLevel(
    key=TARGET_KEY,
    category="Dwelling",
    name_key=None,
    scene_slot=None,
    cost=ResourceCost(gold=3000, wood=5),
    prerequisites=(PRE_KEY,),
)
PRE = BuildingLevel(
    key=PRE_KEY,
    category="Hall",
    name_key=None,
    scene_slot=None,
    cost=ResourceCost(gold=1000),
)
START = BuildingLevel(
    key=START_KEY,
    category="Starting",
    name_key=None,
    scene_slot=None,
    cost=ResourceCost(),
    constructed_on_start=True,
)
PLAN = BuildPlan(
    faction="nature",
    target=TARGET_KEY,
    order_number=1,
    steps=(
        BuildStep(
            1,
            GameDate(1, 1, 1),
            PRE_KEY,
            ResourceCost(gold=1000),
            ResourceCost(gold=1000),
        ),
        BuildStep(
            2,
            GameDate(1, 1, 2),
            TARGET_KEY,
            ResourceCost(gold=3000, wood=5),
            ResourceCost(gold=4000, wood=5),
        ),
    ),
    total_cost=ResourceCost(gold=4000, wood=5),
    starting_date=GameDate(1, 1, 1),
)
ZERO = BuildPlan(
    faction="nature",
    target=START_KEY,
    order_number=1,
    steps=(),
    total_cost=ResourceCost(),
    starting_date=GameDate(1, 1, 1),
)

UNDEAD_TARGET_KEY = BuildingKey("undead", "Build_Tier_6", 1)
UNDEAD_TIER_3_KEY = BuildingKey("undead", "Build_Tier_3", 1)
UNDEAD_WALL_KEY = BuildingKey("undead", "Build_Wall", 1)

UNDEAD_TIER_3 = BuildingLevel(
    key=UNDEAD_TIER_3_KEY,
    category="Dwelling",
    name_key=None,
    scene_slot=None,
    cost=ResourceCost(gold=3000, wood=5, ore=5),
)
UNDEAD_WALL = BuildingLevel(
    key=UNDEAD_WALL_KEY,
    category="Fortification",
    name_key=None,
    scene_slot=None,
    cost=ResourceCost(gold=2500, wood=5, ore=5),
    constructed_on_start=True,
)
UNDEAD_TARGET = BuildingLevel(
    key=UNDEAD_TARGET_KEY,
    category="Dwelling",
    name_key=None,
    scene_slot=None,
    cost=ResourceCost(gold=6000, wood=10, ore=5),
    prerequisites=(UNDEAD_TIER_3_KEY, UNDEAD_WALL_KEY),
)
UNDEAD_PLAN = BuildPlan(
    faction="undead",
    target=UNDEAD_TARGET_KEY,
    order_number=1,
    steps=(
        BuildStep(
            1,
            GameDate(1, 1, 1),
            UNDEAD_TIER_3_KEY,
            ResourceCost(gold=3000, wood=5, ore=5),
            ResourceCost(gold=3000, wood=5, ore=5),
        ),
        BuildStep(
            2,
            GameDate(1, 1, 2),
            UNDEAD_TARGET_KEY,
            ResourceCost(gold=6000, wood=10, ore=5),
            ResourceCost(gold=9000, wood=15, ore=10),
        ),
    ),
    total_cost=ResourceCost(gold=9000, wood=15, ore=10),
    starting_date=GameDate(1, 1, 1),
)


class Service:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.fail = False

    def list_factions(self) -> tuple[str, ...]:
        return ("nature",)

    def list_buildings(self, faction: str) -> tuple[str, ...]:
        return ("Build_Start", "Build_Tier_4")

    def list_building_levels(
        self,
        faction: str,
        sid: str,
    ) -> tuple[int, ...]:
        return (1,) if sid == "Build_Start" else (2,)

    def get_building(
        self,
        faction: str,
        sid: str,
        level: int,
    ) -> BuildingLevel:
        self.calls.append(("get_building", faction, sid, level))
        if self.fail:
            raise QueryError("simulated generation failure")
        return START if sid == "Build_Start" else TARGET

    def get_prerequisites(
        self,
        faction: str,
        sid: str,
        level: int,
    ) -> tuple[BuildingLevel, ...]:
        self.calls.append(("get_prerequisites", faction, sid, level))
        return () if sid == "Build_Start" else (PRE,)

    def generate_build_plan(
        self,
        faction: str,
        sid: str,
        level: int,
    ) -> BuildPlan:
        self.calls.append(("generate_build_plan", faction, sid, level))
        return ZERO if sid == "Build_Start" else PLAN

    def get_cumulative_cost(
        self,
        faction: str,
        sid: str,
        level: int,
    ) -> ResourceCost:
        self.calls.append(("get_cumulative_cost", faction, sid, level))
        return ResourceCost() if sid == "Build_Start" else PLAN.total_cost


class View:
    def __init__(self) -> None:
        self.generate_enabled = False
        self.target: BuildingLevel | None = None
        self.prerequisites: tuple[BuildingLevel, ...] | None = None
        self.plan: BuildPlan | None = None
        self.cost: ResourceCost | None = None
        self.error: str | None = None

    def set_event_handlers(
        self,
        **kwargs: Callable[..., None],
    ) -> None:
        pass

    def set_factions(self, factions: tuple[str, ...]) -> None:
        pass

    def set_buildings(self, buildings: tuple[str, ...]) -> None:
        pass

    def set_levels(self, levels: tuple[int, ...]) -> None:
        pass

    def clear_building_selection(self) -> None:
        pass

    def clear_level_selection(self) -> None:
        pass

    def set_generate_enabled(self, enabled: bool) -> None:
        self.generate_enabled = enabled

    def clear_results(self) -> None:
        self.target = None
        self.prerequisites = None
        self.plan = None
        self.cost = None
        self.error = None

    def show_target(self, building: BuildingLevel) -> None:
        self.target = building

    def show_prerequisites(
        self,
        prerequisites: tuple[BuildingLevel, ...],
    ) -> None:
        self.prerequisites = prerequisites

    def show_plan(
        self,
        plan: BuildPlan,
        cumulative_cost: ResourceCost,
    ) -> None:
        self.plan = plan
        self.cost = cumulative_cost

    def show_error(self, message: str) -> None:
        self.error = message


def select(
    presenter: PlannerPresenter,
    sid: str = "Build_Tier_4",
    level: int = 2,
) -> None:
    presenter.on_faction_changed("nature")
    presenter.on_building_changed(sid)
    presenter.on_level_changed(level)


def validate_starting_prerequisite_presentation() -> None:
    prerequisites = (UNDEAD_TIER_3, UNDEAD_WALL)
    formatted_prerequisites = format_prerequisites(prerequisites)

    required_text = (
        "1. Faction: undead | SID: Build_Tier_3 | Level: 1\n"
        "   Status: Requires construction"
    )
    starting_text = (
        "2. Faction: undead | SID: Build_Wall | Level: 1\n"
        "   Status: Already constructed at game start"
    )

    if required_text not in formatted_prerequisites:
        raise RuntimeError(
            "Ordinary prerequisite was not labeled as requiring construction"
        )
    if starting_text not in formatted_prerequisites:
        raise RuntimeError(
            "Constructed-at-start prerequisite was not labeled clearly"
        )
    if "do not appear as construction actions" not in formatted_prerequisites:
        raise RuntimeError(
            "Starting-prerequisite explanation was not displayed"
        )

    step_keys = tuple(step.building for step in UNDEAD_PLAN.steps)
    if step_keys != (UNDEAD_TIER_3_KEY, UNDEAD_TARGET_KEY):
        raise RuntimeError(
            "Undead plan did not preserve the expected construction sequence"
        )
    if UNDEAD_WALL_KEY in step_keys:
        raise RuntimeError(
            "Constructed-at-start wall was incorrectly added as a build step"
        )
    if UNDEAD_PLAN.build_actions != 2:
        raise RuntimeError(
            "Undead Build_Tier_6 plan should contain exactly two actions"
        )

    expected_cost = ResourceCost(gold=9000, wood=15, ore=10)
    if UNDEAD_PLAN.total_cost != expected_cost:
        raise RuntimeError(
            "Undead Build_Tier_6 cumulative cost changed unexpectedly"
        )

    formatted_plan = format_build_plan(UNDEAD_PLAN)
    if "Total construction actions: 2" not in formatted_plan:
        raise RuntimeError(
            "Formatted undead plan did not show two construction actions"
        )
    if "SID: Build_Wall" in formatted_plan:
        raise RuntimeError(
            "Starting wall appeared in the formatted construction sequence"
        )
    if format_resource_cost(UNDEAD_PLAN.total_cost) != (
        "gold: 9000, wood: 15, ore: 10"
    ):
        raise RuntimeError(
            "Undead Build_Tier_6 total cost formatting changed unexpectedly"
        )


def main() -> None:
    service = Service()
    state = PlannerState()
    view = View()
    statuses: list[str] = []
    presenter = PlannerPresenter(
        service,
        state,
        view,
        statuses.append,
    )  # type: ignore[arg-type]

    presenter.initialize()
    presenter.on_generate_plan()
    if service.calls or view.generate_enabled:
        raise RuntimeError("Incomplete state was not rejected")

    select(presenter)
    presenter.on_generate_plan()
    expected_calls = [
        ("get_building", "nature", "Build_Tier_4", 2),
        ("get_prerequisites", "nature", "Build_Tier_4", 2),
        ("generate_build_plan", "nature", "Build_Tier_4", 2),
        ("get_cumulative_cost", "nature", "Build_Tier_4", 2),
    ]
    if service.calls != expected_calls:
        raise RuntimeError(f"Unexpected calls: {service.calls}")
    if (
        view.target,
        view.prerequisites,
        view.plan,
        view.cost,
    ) != (
        TARGET,
        (PRE,),
        PLAN,
        PLAN.total_cost,
    ):
        raise RuntimeError("Results not displayed")

    first = (
        view.target,
        view.prerequisites,
        view.plan,
        view.cost,
        statuses[-1],
    )
    service.calls.clear()
    presenter.on_generate_plan()
    second = (
        view.target,
        view.prerequisites,
        view.plan,
        view.cost,
        statuses[-1],
    )
    if first != second or service.calls != expected_calls:
        raise RuntimeError("Repeated generation was not deterministic")

    presenter.on_level_changed(2)
    if state.current_plan is not None or view.plan is not None:
        raise RuntimeError("Level change did not clear results")

    select(presenter, "Build_Start", 1)
    presenter.on_generate_plan()
    if (
        view.target,
        view.prerequisites,
        view.plan,
        view.cost,
    ) != (
        START,
        (),
        ZERO,
        ResourceCost(),
    ):
        raise RuntimeError("Zero-action result incorrect")
    if format_prerequisites(()) != "No direct prerequisites.":
        raise RuntimeError("No-prerequisite output changed unexpectedly")
    if "no construction actions" not in statuses[-1].lower():
        raise RuntimeError("Zero-action status unclear")

    service.fail = True
    select(presenter)
    presenter.on_generate_plan()
    if (
        state.current_plan is not None
        or view.plan is not None
        or view.target is not None
    ):
        raise RuntimeError("Failure retained stale results")
    if view.error is None or not state.has_complete_target:
        raise RuntimeError("Failure handling incorrect")

    validate_starting_prerequisite_presentation()

    print("Desktop plan-generation validation completed successfully.")
    print("All four Query Layer planning operations used canonical arguments.")
    print("Target, prerequisites, dated plan, and cumulative cost were displayed.")
    print("Repeated generation returned deterministic results.")
    print(
        "Constructed-at-start targets produced understandable zero-action output."
    )
    print(
        "Starting prerequisites were labeled without changing plan steps or cost."
    )
    print(
        "Undead Build_Tier_6 retained two actions and "
        "9000 gold, 15 wood, 10 ore total cost."
    )
    print("Selection changes and Query errors cleared stale results.")
    print("Presenter logic was validated without live tkinter widgets.")


if __name__ == "__main__":
    main()
