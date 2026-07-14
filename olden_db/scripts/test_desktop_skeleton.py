from __future__ import annotations

from collections.abc import Callable

from olden_db.desktop.formatting import format_faction_status
from olden_db.desktop.presenters.planner_presenter import PlannerPresenter
from olden_db.desktop.state import PlannerState
from olden_db.models import BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan


class StubQueryService:
    def list_factions(self) -> tuple[str, ...]:
        return ("demon", "nature")


class StubView:
    def __init__(self) -> None:
        self.handlers: dict[str, Callable[..., None]] = {}
        self.factions: tuple[str, ...] = ()
        self.generate_enabled = True
        self.clear_results_count = 0

    def set_event_handlers(
        self,
        *,
        on_faction_changed: Callable[[str], None],
        on_building_changed: Callable[[str], None],
        on_level_changed: Callable[[int], None],
        on_generate_plan: Callable[[], None],
    ) -> None:
        self.handlers = {
            "faction": on_faction_changed,
            "building": on_building_changed,
            "level": on_level_changed,
            "generate": on_generate_plan,
        }

    def set_factions(self, factions: tuple[str, ...]) -> None:
        self.factions = factions

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
        self.clear_results_count += 1

    def show_target(self, building: BuildingLevel) -> None:
        raise RuntimeError("Skeleton initialization should not display a target")

    def show_prerequisites(
        self, prerequisites: tuple[BuildingLevel, ...]
    ) -> None:
        raise RuntimeError(
            "Skeleton initialization should not display prerequisites"
        )

    def show_plan(
        self, plan: BuildPlan, cumulative_cost: ResourceCost
    ) -> None:
        raise RuntimeError("Skeleton initialization should not display a plan")

    def show_error(self, message: str) -> None:
        raise RuntimeError("Skeleton initialization should not display an error")


def main() -> None:
    state = PlannerState()
    view = StubView()
    statuses: list[str] = []

    presenter = PlannerPresenter(
        service=StubQueryService(),  # type: ignore[arg-type]
        state=state,
        view=view,
        set_status=statuses.append,
    )
    presenter.initialize()

    if statuses != ["Ready — 2 factions available."]:
        raise RuntimeError(f"Unexpected initial desktop status: {statuses!r}")
    if view.factions != ("demon", "nature"):
        raise RuntimeError("Initial faction discovery was not passed to the view")
    if view.generate_enabled:
        raise RuntimeError("Generate Plan was enabled during skeleton initialization")
    if view.clear_results_count != 1:
        raise RuntimeError("Initial results were not cleared exactly once")
    if set(view.handlers) != {"faction", "building", "level", "generate"}:
        raise RuntimeError("Presenter did not register the complete view contract")
    if format_faction_status(1) != "Ready — 1 faction available.":
        raise RuntimeError("Singular faction status formatting was incorrect")
    if state != PlannerState():
        raise RuntimeError(
            "Desktop initialization unexpectedly changed planner state"
        )

    print("Desktop skeleton validation completed successfully.")
    print("Presenter initialized through Query Layer discovery.")
    print("Expanded semantic view contract initialized correctly.")
    print("Initial planner selection and result state remained empty.")


if __name__ == "__main__":
    main()
