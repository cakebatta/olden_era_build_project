from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ComparisonPresentationStatus(str, Enum):
    UNAVAILABLE = "unavailable"
    WAITING = "waiting"
    READY = "ready"
    FAILURE = "failure"


@dataclass(frozen=True, slots=True)
class ResourceDeltaPresentation:
    resource_name: str
    value_text: str


@dataclass(frozen=True, slots=True)
class ComparisonSideStepPresentation:
    building_name: str
    level_text: str
    date_text: str


@dataclass(frozen=True, slots=True)
class AlignedStepComparisonPresentation:
    position: int
    left: ComparisonSideStepPresentation | None
    relationship: str
    relationship_key: str
    right: ComparisonSideStepPresentation | None


@dataclass(frozen=True, slots=True)
class ComparisonActionPresentation:
    building_name: str
    level_text: str
    date_text: str


@dataclass(frozen=True, slots=True)
class BuildPlanComparisonSummaryPresentation:
    left_label: str
    right_label: str
    left_completion_date: str
    right_completion_date: str
    completion_date_delta: str
    left_construction_count: str
    right_construction_count: str
    construction_count_delta: str
    equivalent_text: str


@dataclass(frozen=True, slots=True)
class BuildPlanComparisonPresentation:
    status: ComparisonPresentationStatus
    heading: str
    detail: str
    retained_previous_comparison: bool = False
    summary: BuildPlanComparisonSummaryPresentation | None = None
    resource_deltas: tuple[ResourceDeltaPresentation, ...] = ()
    aligned_steps: tuple[AlignedStepComparisonPresentation, ...] = ()
    shared_actions: tuple[ComparisonActionPresentation, ...] = ()
    left_only_actions: tuple[ComparisonActionPresentation, ...] = ()
    right_only_actions: tuple[ComparisonActionPresentation, ...] = ()
