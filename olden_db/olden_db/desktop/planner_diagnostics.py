from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DiagnosticSeverity(str, Enum):
    """Presentation severity supplied to the read-only constraint inspector."""

    ERROR = "Error"
    WARNING = "Warning"
    INFORMATION = "Information"


@dataclass(frozen=True, slots=True)
class PlannerDiagnosticPresentation:
    """Immutable planner-provided diagnostic prepared for desktop rendering."""

    title: str
    explanation: str
    severity: DiagnosticSeverity

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("diagnostic title cannot be blank")
        if not self.explanation.strip():
            raise ValueError("diagnostic explanation cannot be blank")
        if not isinstance(self.severity, DiagnosticSeverity):
            raise TypeError("severity must be a DiagnosticSeverity")
