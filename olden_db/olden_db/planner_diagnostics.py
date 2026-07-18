from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import BuildingKey


class PlannerDiagnosticCategory(str, Enum):
    """Stable backend categories for planner-owned diagnostic facts."""

    INVALID_REQUEST = "invalid_request"
    INVALID_BUILD_ORDER = "invalid_build_order"
    DATA_INTEGRITY = "data_integrity"
    CONSISTENCY = "consistency"


@dataclass(frozen=True, slots=True)
class PlannerDiagnostic:
    """
    Immutable planner-owned diagnostic.

    This model contains canonical planner facts only. Presentation severity,
    icons, colors, ordering, grouping, localization, and display formatting
    belong to presentation adapters.
    """

    diagnostic_code: str
    category: PlannerDiagnosticCategory
    canonical_explanation: str
    affected_entities: tuple[BuildingKey, ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.diagnostic_code.strip():
            raise ValueError("diagnostic_code cannot be blank")
        if not isinstance(self.category, PlannerDiagnosticCategory):
            raise TypeError("category must be a PlannerDiagnosticCategory")
        if not self.canonical_explanation.strip():
            raise ValueError("canonical_explanation cannot be blank")

        normalized_entities = tuple(self.affected_entities)
        if any(not isinstance(entity, BuildingKey) for entity in normalized_entities):
            raise TypeError("affected_entities must contain BuildingKey values")
        object.__setattr__(self, "affected_entities", normalized_entities)

        normalized_metadata = tuple(self.metadata)
        for key, value in normalized_metadata:
            if not isinstance(key, str) or not key.strip():
                raise ValueError("diagnostic metadata keys must be non-blank strings")
            if not isinstance(value, str):
                raise TypeError("diagnostic metadata values must be strings")
        object.__setattr__(self, "metadata", normalized_metadata)
