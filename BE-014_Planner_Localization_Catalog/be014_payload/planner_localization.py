from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .database import LoadedGameData
from .localization import LocalizationCatalog
from .models import BuildingKey


class PlannerLocalizationError(ValueError):
    """Base error for planner-localization catalog construction."""


class PlannerLocalizationConflictError(PlannerLocalizationError):
    """Raised when equal-precedence sources disagree for one planner entity."""


@dataclass(frozen=True, slots=True)
class PlannerLocalizationCatalog:
    """Immutable planner-scoped display-name index for one language."""

    language: str
    _faction_names: Mapping[str, str]
    _building_names: Mapping[BuildingKey, str]
    _unit_names: Mapping[tuple[str, str], str]
    _upgrade_names: Mapping[tuple[str, str], str]

    def __post_init__(self) -> None:
        if not isinstance(self.language, str) or not self.language:
            raise ValueError("language cannot be empty")
        object.__setattr__(self, "_faction_names", MappingProxyType(dict(self._faction_names)))
        object.__setattr__(self, "_building_names", MappingProxyType(dict(self._building_names)))
        object.__setattr__(self, "_unit_names", MappingProxyType(dict(self._unit_names)))
        object.__setattr__(self, "_upgrade_names", MappingProxyType(dict(self._upgrade_names)))

    def get_faction_display_name(self, faction_sid: str) -> str:
        _require_identifier(faction_sid, "faction_sid")
        return self._faction_names[faction_sid]

    def get_building_display_name(self, building: BuildingKey) -> str:
        if not isinstance(building, BuildingKey):
            raise TypeError("building must be a BuildingKey")
        return self._building_names[building]

    def get_unit_display_name(self, faction_sid: str, unit_sid: str) -> str:
        _require_identifier(faction_sid, "faction_sid")
        _require_identifier(unit_sid, "unit_sid")
        return self._unit_names[(faction_sid, unit_sid)]

    def get_upgrade_display_name(self, faction_sid: str, upgrade_sid: str) -> str:
        _require_identifier(faction_sid, "faction_sid")
        _require_identifier(upgrade_sid, "upgrade_sid")
        return self._upgrade_names[(faction_sid, upgrade_sid)]


def build_planner_localization_catalog(
    data: LoadedGameData,
    localization: LocalizationCatalog,
) -> PlannerLocalizationCatalog:
    """Build one immutable planner-only display-name catalog."""
    if not isinstance(data, LoadedGameData):
        raise TypeError("data must be LoadedGameData")
    if not isinstance(localization, LocalizationCatalog):
        raise TypeError("localization must be LocalizationCatalog")

    faction_names: dict[str, str] = {}
    building_names: dict[BuildingKey, str] = {}
    unit_names: dict[tuple[str, str], str] = {}
    upgrade_names: dict[tuple[str, str], str] = {}

    for faction_sid in sorted(data.cities.cities):
        city = data.cities.city(faction_sid)
        faction_names[faction_sid] = _resolve(
            localization,
            candidates=(city.city_id, f"{faction_sid}_name"),
            canonical_display=None,
            canonical_identifier=faction_sid,
        )
        for building_key in sorted(city.buildings, key=lambda item: (item.sid, item.level)):
            definition = city.buildings[building_key]
            building_names[building_key] = _resolve(
                localization,
                candidates=(definition.name_key,),
                canonical_display=None,
                canonical_identifier=building_key.sid,
            )

    for definition in sorted(
        data.units.units.values(),
        key=lambda item: (item.faction, item.tier, item.sid),
    ):
        key = (definition.faction, definition.sid)
        display = _resolve(
            localization,
            candidates=(definition.sid,),
            canonical_display=None,
            canonical_identifier=definition.sid,
        )
        unit_names[key] = display
        if "_upg" in definition.sid or definition.upgrade_sid is not None:
            upgrade_names[key] = display

    return PlannerLocalizationCatalog(
        language=localization.language,
        _faction_names=faction_names,
        _building_names=building_names,
        _unit_names=unit_names,
        _upgrade_names=upgrade_names,
    )


def _resolve(
    localization: LocalizationCatalog,
    *,
    candidates: tuple[str | None, ...],
    canonical_display: str | None,
    canonical_identifier: str,
) -> str:
    for candidate in candidates:
        if candidate and localization.contains(candidate):
            text = localization.get(candidate)
            if text:
                return text
    if canonical_display:
        return canonical_display
    return canonical_identifier


def _require_identifier(value: str, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value:
        raise ValueError(f"{name} cannot be empty")
