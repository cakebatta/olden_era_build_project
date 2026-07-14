from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PlannerState:
    """Minimal selection state shared by the initial planner modules."""

    selected_faction: str | None = None
    selected_building_sid: str | None = None
    selected_level: int | None = None
