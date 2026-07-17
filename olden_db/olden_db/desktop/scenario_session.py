from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from olden_db.scenario_persistence import ScenarioDocument

class ScenarioSource(str, Enum):
    NEW="new"; MANAGED="managed"; IMPORTED="imported"; DETACHED="detached"

def persisted_content(document: ScenarioDocument) -> tuple[object,...]:
    return (document.name, document.description, document.notes, document.faction,
            document.target, document.starting_date, document.planning_scenario,
            document.starting_resources, document.recruitment_actions)

@dataclass(slots=True)
class ScenarioSession:
    active_document: ScenarioDocument
    repository_token: str|None=None
    saved_snapshot: ScenarioDocument|None=None
    source_state: ScenarioSource=ScenarioSource.NEW
    repository_membership: bool=False
    current_document: ScenarioDocument|None=None
    def __post_init__(self):
        self.current_document=self.current_document or self.active_document
    @property
    def dirty(self)->bool:
        baseline=self.saved_snapshot or self.active_document
        return persisted_content(self.current_document or self.active_document)!=persisted_content(baseline)
    @property
    def has_unsaved_risk(self)->bool:
        return self.dirty or not self.repository_membership
    @property
    def display_name(self)->str:
        return f"{(self.current_document or self.active_document).name}{' *' if self.has_unsaved_risk else ''}"
    def update_candidate(self, document): self.current_document=document
    def accept_saved(self, document, token, *, source=ScenarioSource.MANAGED):
        self.active_document=self.current_document=self.saved_snapshot=document
        self.repository_token=token; self.repository_membership=True; self.source_state=source
    def accept_loaded(self, document, token): self.accept_saved(document, token)
    def detach_after_delete(self):
        document=self.current_document or self.active_document
        self.active_document=self.current_document=document; self.saved_snapshot=None
        self.repository_token=None; self.repository_membership=False; self.source_state=ScenarioSource.DETACHED
