from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PlannerState:
    """Explicit target-selection state for the Build Planner."""

    selected_faction: str | None = None
    selected_building_sid: str | None = None
    selected_level: int | None = None

    @property
    def has_complete_target(self) -> bool:
        return (
            self.selected_faction is not None
            and self.selected_building_sid is not None
            and self.selected_level is not None
        )

    def select_faction(self, faction: str) -> None:
        self.selected_faction = faction
        self.selected_building_sid = None
        self.selected_level = None

    def select_building(self, sid: str) -> None:
        self.selected_building_sid = sid
        self.selected_level = None

    def select_level(self, level: int) -> None:
        self.selected_level = level
