from __future__ import annotations

from dataclasses import dataclass, field

from olden_db.models import ResourceCost
from olden_db.query import ResourceLedger


@dataclass(slots=True)
class EconomyTimelineState:
    """Starting treasury and authoritative ledger result state."""

    starting_resources: ResourceCost = field(default_factory=ResourceCost)
    starting_resources_valid: bool = True
    current_ledger: ResourceLedger | None = None

    def replace_starting_resources(self, resources: ResourceCost) -> None:
        self.starting_resources = resources
        self.starting_resources_valid = True
        self.current_ledger = None

    def invalidate_starting_resources(self) -> None:
        self.starting_resources_valid = False
        self.current_ledger = None

    def clear_ledger(self) -> None:
        self.current_ledger = None
