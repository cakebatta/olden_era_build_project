from __future__ import annotations

from dataclasses import dataclass, field

from olden_db.models import BuildingKey, ResourceCost
from olden_db.planner import GameDate
from olden_db.query import RecruitmentAction, ResourceLedger


@dataclass(frozen=True, slots=True, order=True)
class RecruitmentSelection:
    date: GameDate
    dwelling: BuildingKey
    base_quantity: int = 0
    upgraded_quantity: int = 0

    def __post_init__(self) -> None:
        if self.base_quantity < 0 or self.upgraded_quantity < 0:
            raise ValueError("recruitment quantities cannot be negative")

    @property
    def total_quantity(self) -> int:
        return self.base_quantity + self.upgraded_quantity

    def to_action(self) -> RecruitmentAction | None:
        if self.total_quantity == 0:
            return None
        return RecruitmentAction(
            date=self.date,
            dwelling=self.dwelling,
            base_quantity=self.base_quantity,
            upgraded_quantity=self.upgraded_quantity,
        )


@dataclass(slots=True)
class EconomyTimelineState:
    starting_resources: ResourceCost = field(default_factory=ResourceCost)
    starting_resources_valid: bool = True
    starting_resources_issue: ValueError | None = None
    recruitment_selections: tuple[RecruitmentSelection, ...] = ()
    recruitment_issue: ValueError | None = None
    current_ledger: ResourceLedger | None = None
    control_ledger: ResourceLedger | None = None

    @property
    def recruitment_actions(self) -> tuple[RecruitmentAction, ...]:
        return tuple(
            action
            for selection in self.recruitment_selections
            if (action := selection.to_action()) is not None
        )

    def replace_starting_resources(self, resources: ResourceCost) -> None:
        self.starting_resources = resources
        self.starting_resources_valid = True
        self.starting_resources_issue = None
        self.current_ledger = None

    def invalidate_starting_resources(self, message: str = "Starting resources are invalid.") -> None:
        self.starting_resources_valid = False
        self.starting_resources_issue = ValueError(message)
        self.current_ledger = None

    def mark_recruitment_invalid(self, message: str) -> None:
        self.recruitment_issue = ValueError(message)
        self.current_ledger = None

    def clear_recruitment_issue(self) -> None:
        self.recruitment_issue = None

    def replace_recruitment_selection(
        self,
        selection: RecruitmentSelection,
    ) -> None:
        retained = tuple(
            item
            for item in self.recruitment_selections
            if (item.date, item.dwelling)
            != (selection.date, selection.dwelling)
        )
        updated = (
            retained
            if selection.total_quantity == 0
            else retained + (selection,)
        )
        self.recruitment_selections = tuple(sorted(updated))
        self.recruitment_issue = None
        self.current_ledger = None

    def clear_recruitment(self) -> None:
        self.recruitment_selections = ()
        self.recruitment_issue = None
        self.current_ledger = None
        self.control_ledger = None

    def clear_ledger(self) -> None:
        self.current_ledger = None
