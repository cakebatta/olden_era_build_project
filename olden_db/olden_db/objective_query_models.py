from __future__ import annotations

from dataclasses import dataclass

from .models import BuildingKey, ResourceCost
from .objective_planning import (
    BuildingCompletionObjective,
    Objective,
    ObjectiveSetCompletionState,
    TownPlanningRequest,
)
from .planner import GameDate
from .planner_diagnostics import PlannerDiagnostic


@dataclass(frozen=True, slots=True)
class ObjectiveSummary:
    objective: Objective
    canonical_building: BuildingKey
    display_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.objective, BuildingCompletionObjective):
            raise TypeError("objective must be a supported Objective")
        if self.canonical_building != self.objective.building:
            raise ValueError("canonical_building must match objective identity")
        if not self.display_name.strip():
            raise ValueError("display_name must be non-blank")


@dataclass(frozen=True, slots=True)
class PrerequisiteProvenance:
    objective: ObjectiveSummary
    required_buildings: tuple[BuildingKey, ...]
    required_build_steps: tuple[BuildingKey, ...]
    satisfied_at_start: tuple[BuildingKey, ...]
    prerequisite_relationships: tuple[tuple[BuildingKey, BuildingKey], ...]


@dataclass(frozen=True, slots=True)
class ObjectiveCompletionView:
    objective: ObjectiveSummary
    completed: bool
    completion_day: GameDate | None
    satisfied_at_start: bool
    completing_action: BuildingKey | None
    provenance: PrerequisiteProvenance


@dataclass(frozen=True, slots=True)
class BuildStepExplanation:
    step_number: int
    building: BuildingKey
    display_name: str
    construction_day: GameDate
    resource_cost: ResourceCost
    prerequisite_buildings: tuple[BuildingKey, ...]
    required_by_objectives: tuple[ObjectiveSummary, ...]
    objective_targets: tuple[ObjectiveSummary, ...]
    downstream_buildings_enabled: tuple[BuildingKey, ...]
    resource_balance_before: ResourceCost
    resource_balance_after: ResourceCost
    income_change: ResourceCost


@dataclass(frozen=True, slots=True)
class ObjectivePlanningSummary:
    request: TownPlanningRequest
    objectives: tuple[ObjectiveSummary, ...]
    completion_state: ObjectiveSetCompletionState
    starting_day: GameDate
    completion_day: GameDate
    total_cost: ResourceCost
    build_action_count: int


@dataclass(frozen=True, slots=True)
class MultiObjectivePlanningResultView:
    summary: ObjectivePlanningSummary
    objective_completions: tuple[ObjectiveCompletionView, ...]
    prerequisite_provenance: tuple[PrerequisiteProvenance, ...]
    build_steps: tuple[BuildStepExplanation, ...]
    diagnostics: tuple[PlannerDiagnostic, ...]
