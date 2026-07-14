from __future__ import annotations

from collections.abc import Callable

from olden_db.desktop.presenters.planner_presenter import PlannerPresenter
from olden_db.desktop.state import PlannerState


class StubQueryService:
    def list_factions(self) -> tuple[str, ...]: return ("demon", "nature")
    def list_buildings(self, faction: str) -> tuple[str, ...]:
        return {"demon": ("Build_Bank", "Build_Tier_1"), "nature": ("Build_Hall", "Build_Tier_4")}[faction]
    def list_building_levels(self, faction: str, sid: str) -> tuple[int, ...]:
        return {("demon", "Build_Bank"): (1,), ("demon", "Build_Tier_1"): (1, 2), ("nature", "Build_Hall"): (1, 2, 3), ("nature", "Build_Tier_4"): (1, 2)}[(faction, sid)]


class StubView:
    def __init__(self) -> None:
        self.factions: tuple[str, ...] = ()
        self.buildings: tuple[str, ...] = ()
        self.levels: tuple[int, ...] = ()
        self.generate_enabled = False
        self.handlers: dict[str, Callable[..., None]] = {}
    def set_event_handlers(self, *, on_faction_changed, on_building_changed, on_level_changed, on_generate_plan) -> None:
        self.handlers = {"faction": on_faction_changed, "building": on_building_changed, "level": on_level_changed, "generate": on_generate_plan}
    def set_factions(self, factions: tuple[str, ...]) -> None: self.factions = factions
    def set_buildings(self, buildings: tuple[str, ...]) -> None: self.buildings = buildings
    def set_levels(self, levels: tuple[int, ...]) -> None: self.levels = levels
    def clear_building_selection(self) -> None: self.buildings = ()
    def clear_level_selection(self) -> None: self.levels = ()
    def set_generate_enabled(self, enabled: bool) -> None: self.generate_enabled = enabled


def main() -> None:
    state = PlannerState(); view = StubView(); statuses: list[str] = []
    presenter = PlannerPresenter(StubQueryService(), state, view, statuses.append)  # type: ignore[arg-type]
    presenter.initialize()
    if view.factions != ("demon", "nature"): raise RuntimeError("Faction population was not deterministic")
    if view.generate_enabled: raise RuntimeError("Generate Plan was enabled before target completion")
    if set(view.handlers) != {"faction", "building", "level", "generate"}: raise RuntimeError("Presenter did not register all explicit view handlers")
    presenter.on_faction_changed("nature")
    if state != PlannerState(selected_faction="nature"): raise RuntimeError("Faction selection did not clear downstream state")
    if view.buildings != ("Build_Hall", "Build_Tier_4"): raise RuntimeError("Building population was incorrect")
    presenter.on_building_changed("Build_Tier_4")
    if state != PlannerState(selected_faction="nature", selected_building_sid="Build_Tier_4"): raise RuntimeError("Building selection did not clear level state")
    if view.levels != (1, 2): raise RuntimeError("Level population was incorrect")
    if view.generate_enabled: raise RuntimeError("Generate Plan enabled before level selection")
    presenter.on_level_changed(2)
    if not state.has_complete_target or not view.generate_enabled: raise RuntimeError("Complete target did not enable Generate Plan")
    presenter.on_building_changed("Build_Hall")
    if state.selected_level is not None or view.generate_enabled: raise RuntimeError("Changing building did not clear level or disable Generate Plan")
    presenter.on_level_changed(3)
    presenter.on_faction_changed("demon")
    if state != PlannerState(selected_faction="demon") or view.generate_enabled: raise RuntimeError("Changing faction did not clear downstream state")
    presenter.on_building_changed("Build_Bank"); presenter.on_level_changed(1); presenter.on_generate_plan()
    if statuses[-1] != "Build plan generation will be implemented in the next milestone.": raise RuntimeError("Generate Plan placeholder status was incorrect")
    print("Desktop target-selection validation completed successfully.")
    print("Selector population was deterministic.")
    print("Downstream state reset rules were preserved.")
    print("Generate Plan enablement matched target completeness.")
    print("Presenter logic was validated without live tkinter widgets.")


if __name__ == "__main__": main()
