from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from olden_db.query import PlanningQueryService

from ..formatting import format_faction_status
from ..state import PlannerState


class PlannerViewContract(Protocol):
    """Minimal view contract required by the skeleton presenter."""


class PlannerPresenter:
    """Coordinate initial planner state, view, and Query Layer access."""

    def __init__(
        self,
        service: PlanningQueryService,
        state: PlannerState,
        view: PlannerViewContract,
        set_status: Callable[[str], None],
    ) -> None:
        self._service = service
        self._state = state
        self._view = view
        self._set_status = set_status

    def initialize(self) -> None:
        """Load lightweight discovery information for initial UI feedback."""

        factions = self._service.list_factions()
        self._set_status(format_faction_status(len(factions)))
