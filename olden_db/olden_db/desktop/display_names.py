from __future__ import annotations
from dataclasses import dataclass
from olden_db.models import BuildingKey

@dataclass(frozen=True, slots=True)
class CanonicalDisplayOption:
    canonical_id: str
    display_name: str

@dataclass(frozen=True, slots=True)
class StartingBuildingPresentation:
    building: BuildingKey
    display_name: str
    level_text: str
    canonical_state_text: str
    constructed_on_start: bool
