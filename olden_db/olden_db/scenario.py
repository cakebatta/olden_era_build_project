from __future__ import annotations

from dataclasses import dataclass

from .models import BuildingKey, BuildingLevel, FactionCity


class ScenarioError(ValueError):
    """Base exception for invalid planning scenarios."""


class DuplicateStartingBuildingOverrideError(ScenarioError):
    """Raised when a scenario overrides one building more than once."""


class InvalidStartingBuildingOverrideError(ScenarioError):
    """Raised when a starting-building override is malformed or invalid."""


@dataclass(frozen=True, slots=True, order=True)
class StartingBuildingOverride:
    """Override whether one canonical building is available at plan start."""

    building: BuildingKey
    available_at_start: bool

    def __post_init__(self) -> None:
        if not isinstance(self.building, BuildingKey):
            raise TypeError("building must be a BuildingKey")
        if type(self.available_at_start) is not bool:
            raise TypeError("available_at_start must be a bool")


@dataclass(frozen=True, slots=True)
class PlanningScenario:
    """Immutable hypothetical starting-state overrides for one plan."""

    starting_building_overrides: tuple[StartingBuildingOverride, ...] = ()

    def __post_init__(self) -> None:
        overrides = tuple(self.starting_building_overrides)
        if any(
            not isinstance(override, StartingBuildingOverride)
            for override in overrides
        ):
            raise TypeError(
                "starting_building_overrides must contain "
                "StartingBuildingOverride values"
            )

        buildings = tuple(override.building for override in overrides)
        if len(buildings) != len(set(buildings)):
            raise DuplicateStartingBuildingOverrideError(
                "A planning scenario cannot override the same building twice"
            )

        object.__setattr__(
            self,
            "starting_building_overrides",
            tuple(sorted(overrides)),
        )


@dataclass(frozen=True, slots=True)
class PrerequisiteStatus:
    """Effective scenario status for one direct prerequisite building."""

    building: BuildingLevel
    available_at_start: bool
    overridden: bool

    def __post_init__(self) -> None:
        if not isinstance(self.building, BuildingLevel):
            raise TypeError("building must be a BuildingLevel")
        if type(self.available_at_start) is not bool:
            raise TypeError("available_at_start must be a bool")
        if type(self.overridden) is not bool:
            raise TypeError("overridden must be a bool")


def resolve_effective_starting_buildings(
    city: FactionCity,
    scenario: PlanningScenario,
) -> frozenset[BuildingKey]:
    """Resolve canonical starting state plus validated scenario overrides."""
    if not isinstance(scenario, PlanningScenario):
        raise TypeError("scenario must be a PlanningScenario")

    effective = {
        key
        for key, building in city.buildings.items()
        if building.constructed_on_start
    }

    for override in scenario.starting_building_overrides:
        key = override.building
        if key.faction != city.faction:
            raise InvalidStartingBuildingOverrideError(
                f"Override faction {key.faction!r} does not match city "
                f"faction {city.faction!r}: {key}"
            )
        if key not in city.buildings:
            raise InvalidStartingBuildingOverrideError(
                f"Unknown starting-building override: {key}"
            )

        if override.available_at_start:
            effective.add(key)
        else:
            effective.discard(key)

    return frozenset(effective)
