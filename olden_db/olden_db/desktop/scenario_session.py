from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from olden_db.scenario_persistence import ScenarioDocument


class ScenarioSource(str, Enum):
    NEW = "new"
    MANAGED = "managed"
    IMPORTED = "imported"
    DETACHED = "detached"


def persisted_content(document: ScenarioDocument) -> tuple[object, ...]:
    return (
        document.name,
        document.description,
        document.notes,
        document.faction,
        document.target,
        document.starting_date,
        document.planning_scenario,
        document.starting_resources,
        document.recruitment_actions,
    )


@dataclass(slots=True)
class ScenarioSession:
    active_document: ScenarioDocument
    repository_token: str | None = None
    saved_snapshot: ScenarioDocument | None = None
    source_state: ScenarioSource = ScenarioSource.NEW
    repository_membership: bool = False
    current_document: ScenarioDocument | None = None
    last_valid_candidate: ScenarioDocument | None = None
    raw_ui_edited: bool = False
    validation_issue: Exception | None = None

    def __post_init__(self) -> None:
        candidate = self.current_document or self.active_document
        self.current_document = candidate
        self.last_valid_candidate = self.last_valid_candidate or candidate

    @property
    def dirty(self) -> bool:
        if self.raw_ui_edited:
            return True
        baseline = self.saved_snapshot or self.active_document
        candidate = self.current_document or self.active_document
        return persisted_content(candidate) != persisted_content(baseline)

    @property
    def invalid(self) -> bool:
        return self.validation_issue is not None

    @property
    def has_unsaved_risk(self) -> bool:
        return (
            self.raw_ui_edited
            or self.dirty
            or not self.repository_membership
        )

    @property
    def display_name(self) -> str:
        document = self.current_document or self.active_document
        marker = " *" if self.has_unsaved_risk else ""
        return f"{document.name}{marker}"

    def mark_ui_edited(self) -> None:
        self.raw_ui_edited = True

    def mark_invalid_edit(self, issue: Exception) -> None:
        self.validation_issue = issue
        self.raw_ui_edited = True

    def update_candidate(self, document: ScenarioDocument) -> None:
        self.current_document = document
        self.last_valid_candidate = document
        self.validation_issue = None

    def reconcile_dirty_state(self) -> None:
        baseline = self.saved_snapshot or self.active_document
        candidate = self.current_document or self.active_document
        self.raw_ui_edited = (
            persisted_content(candidate) != persisted_content(baseline)
        )

    def accept_saved(
        self,
        document: ScenarioDocument,
        token: str,
        *,
        source: ScenarioSource = ScenarioSource.MANAGED,
    ) -> None:
        self.active_document = document
        self.current_document = document
        self.last_valid_candidate = document
        self.saved_snapshot = document
        self.repository_token = token
        self.repository_membership = True
        self.source_state = source
        self.raw_ui_edited = False
        self.validation_issue = None

    def accept_loaded(
        self,
        document: ScenarioDocument,
        token: str,
    ) -> None:
        self.accept_saved(document, token)

    def detach_after_delete(self) -> None:
        document = self.current_document or self.active_document
        self.active_document = document
        self.current_document = document
        self.last_valid_candidate = document
        self.saved_snapshot = None
        self.repository_token = None
        self.repository_membership = False
        self.source_state = ScenarioSource.DETACHED
        self.raw_ui_edited = False
        self.validation_issue = None
