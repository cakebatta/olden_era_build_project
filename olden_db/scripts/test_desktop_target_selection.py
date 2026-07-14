from __future__ import annotations

from collections.abc import Callable

from olden_db.desktop.presenters.planner_presenter import PlannerPresenter
from olden_db.desktop.state import PlannerState
from olden_db.models import BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan
from olden_db.query import QueryError


class StubQueryService:
    def __init__(self) -> None:
        self.rejected_factions: set[str] = set()
        self.rejected_buildings: set[tuple[str, str]] = set()

    def list_factions(self) -> tuple[str, ...]:
        return ("demon", "nature")

    def list_buildings(self, faction: str) -> tuple[str, ...]:
        if faction in self.rejected_factions:
            raise QueryError(f"Unknown faction: {faction!r}")
        return {
            "demon": ("Build_Bank", "Build_Tier_1"),
            "nature": ("Build_Hall", "Build_Tier_4"),
        }[faction]

    def list_building_levels(self, faction: str, sid: str) -> tuple[int, ...]:
        if (faction, sid) in self.rejected_buildings:
            raise QueryError(
                f"Unknown building: faction={faction!r}, sid={sid!r}"
            )
        return {
            ("demon", "Build_Bank"): (1,),
            ("demon", "Build_Tier_1"): (1, 2),
            ("nature", "Build_Hall"): (1, 2, 3),
            ("nature", "Build_Tier_4"): (1, 2),
        }[(faction, sid)]


class StubView:
    def __init__(self) -> None:
        self.factions: tuple[str, ...] = ()
        self.buildings: tuple[str, ...] = ()
        self.levels: tuple[int, ...] = ()
        self.generate_enabled = False
        self.handlers: dict[str, Callable[..., None]] = {}
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
        self.buildings = buildings

    def set_levels(self, levels: tuple[int, ...]) -> None:
        self.levels = levels

    def clear_building_selection(self) -> None:
        self.buildings = ()

    def clear_level_selection(self) -> None:
        self.levels = ()

    def set_generate_enabled(self, enabled: bool) -> None:
        self.generate_enabled = enabled

    def clear_results(self) -> None:
        self.clear_results_count += 1

    def show_target(self, building: BuildingLevel) -> None:
        raise RuntimeError("Target display should not be used in selection validation")

    def show_prerequisites(
        self, prerequisites: tuple[BuildingLevel, ...]
    ) -> None:
        raise RuntimeError(
            "Prerequisite display should not be used in selection validation"
        )

    def show_plan(
        self, plan: BuildPlan, cumulative_cost: ResourceCost
    ) -> None:
        raise RuntimeError("Plan display should not be used in selection validation")

    def show_error(self, message: str) -> None:
        raise RuntimeError("Error display should not be used in selection validation")


def main() -> None:
    service = StubQueryService()
    state = PlannerState()
    view = StubView()
    statuses: list[str] = []

    presenter = PlannerPresenter(
        service,  # type: ignore[arg-type]
        state,
        view,
        statuses.append,
    )
    presenter.initialize()

    if view.factions != ("demon", "nature"):
        raise RuntimeError("Faction population was not deterministic")
    if view.generate_enabled:
        raise RuntimeError("Generate Plan was enabled before target completion")
    if set(view.handlers) != {"faction", "building", "level", "generate"}:
        raise RuntimeError("Presenter did not register all explicit view handlers")

    presenter.on_faction_changed("nature")
    if state != PlannerState(selected_faction="nature"):
        raise RuntimeError("Validated faction selection was not committed correctly")
    if view.buildings != ("Build_Hall", "Build_Tier_4"):
        raise RuntimeError("Building population was incorrect")

    presenter.on_building_changed("Build_Tier_4")
    if state != PlannerState(
        selected_faction="nature",
        selected_building_sid="Build_Tier_4",
    ):
        raise RuntimeError("Validated building selection was not committed correctly")
    if view.levels != (1, 2):
        raise RuntimeError("Level population was incorrect")
    if view.generate_enabled:
        raise RuntimeError("Generate Plan enabled before level selection")

    presenter.on_level_changed(2)
    if not state.has_complete_target or not view.generate_enabled:
        raise RuntimeError("Complete target did not enable Generate Plan")

    presenter.on_building_changed("Build_Hall")
    if state.selected_level is not None or view.generate_enabled:
        raise RuntimeError(
            "Changing building did not clear level or disable Generate Plan"
        )

    presenter.on_level_changed(3)
    presenter.on_faction_changed("demon")
    if state != PlannerState(selected_faction="demon") or view.generate_enabled:
        raise RuntimeError("Changing faction did not clear downstream state")

    validated_state = PlannerState(
        selected_faction="demon",
        selected_building_sid=None,
        selected_level=None,
    )

    service.rejected_factions.add("invalid_faction")
    presenter.on_faction_changed("invalid_faction")
    if state != validated_state:
        raise RuntimeError("Rejected faction was retained in PlannerState")
    if view.generate_enabled:
        raise RuntimeError(
            "Generate Plan remained enabled after failed faction discovery"
        )

    service.rejected_buildings.add(("demon", "invalid_building"))
    presenter.on_building_changed("invalid_building")
    if state != validated_state:
        raise RuntimeError("Rejected building was retained in PlannerState")
    if view.generate_enabled:
        raise RuntimeError(
            "Generate Plan remained enabled after failed building discovery"
        )

    print("Desktop target-selection validation completed successfully.")
    print("Selector population was deterministic.")
    print("Downstream state reset rules were preserved.")
    print("Generate Plan enablement matched target completeness.")
    print("Rejected selections were not retained in PlannerState.")
    print("Negative Query Layer paths kept Generate Plan disabled.")
    print("Expanded result-view contract remained unused by selection tests.")
    print("Presenter logic was validated without live tkinter widgets.")


if __name__ == "__main__":
    main()
