from __future__ import annotations

from dataclasses import dataclass

from .comparison import PlanComparison
from .constants import RESOURCE_NAMES
from .models import BuildingKey


@dataclass(frozen=True, slots=True)
class PlansIdenticalObservation:
    """Record that the compared plans are meaningfully identical."""


@dataclass(frozen=True, slots=True)
class PlansDifferObservation:
    """Record that the compared plans are not meaningfully identical."""


@dataclass(frozen=True, slots=True)
class ActionDeltaObservation:
    """Record the right-minus-left construction-action difference."""

    delta_actions: int


@dataclass(frozen=True, slots=True)
class CompletionDeltaObservation:
    """Record the right-minus-left completion-date difference in days."""

    delta_days: int


@dataclass(frozen=True, slots=True)
class ResourceDeltaObservation:
    """Record one right-minus-left canonical resource difference."""

    resource: str
    delta: int

    def __post_init__(self) -> None:
        if self.resource not in RESOURCE_NAMES:
            raise ValueError(f"Unknown resource name: {self.resource!r}")
        if self.delta == 0:
            raise ValueError("resource delta observation cannot be zero")


@dataclass(frozen=True, slots=True)
class BuildingAddedObservation:
    """Record a construction action present only in the right plan."""

    building: BuildingKey


@dataclass(frozen=True, slots=True)
class BuildingRemovedObservation:
    """Record a construction action present only in the left plan."""

    building: BuildingKey


DecisionObservation = (
    PlansIdenticalObservation
    | PlansDifferObservation
    | ActionDeltaObservation
    | CompletionDeltaObservation
    | ResourceDeltaObservation
    | BuildingAddedObservation
    | BuildingRemovedObservation
)


@dataclass(frozen=True, slots=True)
class DecisionSummary:
    """Immutable structured interpretation of one completed plan comparison."""

    comparison: PlanComparison
    observations: tuple[DecisionObservation, ...]


def summarize_plan_comparison(comparison: PlanComparison) -> DecisionSummary:
    """Return deterministic structured facts derived only from ``comparison``.

    Numeric values preserve the comparison module's ``right - left`` direction.
    The function performs no planning, graph traversal, scenario resolution,
    ranking, recommendation, presentation formatting, or I/O.
    """
    if not isinstance(comparison, PlanComparison):
        raise TypeError("comparison must be a PlanComparison")

    observations: list[DecisionObservation] = [
        (
            PlansIdenticalObservation()
            if comparison.identical
            else PlansDifferObservation()
        )
    ]

    if comparison.action_delta != 0:
        observations.append(
            ActionDeltaObservation(delta_actions=comparison.action_delta)
        )

    if comparison.completion_date_delta != 0:
        observations.append(
            CompletionDeltaObservation(
                delta_days=comparison.completion_date_delta
            )
        )

    for resource in RESOURCE_NAMES:
        delta = getattr(comparison.resource_delta, resource)
        if delta != 0:
            observations.append(
                ResourceDeltaObservation(resource=resource, delta=delta)
            )

    observations.extend(
        BuildingAddedObservation(building=building)
        for building in sorted(comparison.added_buildings)
    )
    observations.extend(
        BuildingRemovedObservation(building=building)
        for building in sorted(comparison.removed_buildings)
    )

    return DecisionSummary(
        comparison=comparison,
        observations=tuple(observations),
    )
