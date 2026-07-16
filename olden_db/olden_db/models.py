from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from .constants import RESOURCE_NAMES


@dataclass(frozen=True, slots=True)
class ResourceCost:
    """A fixed resource vector used for buildings and units."""

    gold: int = 0
    wood: int = 0
    ore: int = 0
    gemstones: int = 0
    crystals: int = 0
    mercury: int = 0
    dust: int = 0
    graal: int = 0

    @classmethod
    def from_entries(cls, entries: Iterable[Mapping[str, object]]) -> "ResourceCost":
        values = {name: 0 for name in RESOURCE_NAMES}
        for entry in entries:
            try:
                name = str(entry["name"])
                cost = int(entry["cost"])
            except KeyError as exc:
                raise ValueError(f"Resource entry is missing field: {exc.args[0]!r}") from exc
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid resource entry: {entry!r}") from exc
            if name not in values:
                raise ValueError(f"Unknown resource name: {name!r}")
            values[name] += cost
        return cls(**values)

    def __add__(self, other: "ResourceCost") -> "ResourceCost":
        if not isinstance(other, ResourceCost):
            return NotImplemented
        return ResourceCost(**{name: getattr(self, name) + getattr(other, name) for name in RESOURCE_NAMES})

    def __sub__(self, other: "ResourceCost") -> "ResourceCost":
        if not isinstance(other, ResourceCost):
            return NotImplemented
        return ResourceCost(**{name: getattr(self, name) - getattr(other, name) for name in RESOURCE_NAMES})

    def as_dict(self) -> dict[str, int]:
        return {name: getattr(self, name) for name in RESOURCE_NAMES}

    def is_zero(self) -> bool:
        return all(getattr(self, name) == 0 for name in RESOURCE_NAMES)


@dataclass(frozen=True, slots=True, order=True)
class BuildingKey:
    faction: str
    sid: str
    level: int

    def __post_init__(self) -> None:
        if not self.faction:
            raise ValueError("faction cannot be empty")
        if not self.sid:
            raise ValueError("sid cannot be empty")
        if self.level < 1:
            raise ValueError("building level must be at least 1")


@dataclass(frozen=True, slots=True)
class UnitFamily:
    faction: str
    tier: int
    dwelling_sid: str
    base_sid: str
    upgrade_option_1_sid: str
    upgrade_option_2_sid: str
    weekly_growth: int
    base_cost: ResourceCost = field(default_factory=ResourceCost)
    upgraded_cost: ResourceCost = field(default_factory=ResourceCost)

    def __post_init__(self) -> None:
        if not self.faction:
            raise ValueError("faction cannot be empty")
        if self.tier < 1:
            raise ValueError("unit tier must be at least 1")
        if not self.dwelling_sid:
            raise ValueError("dwelling_sid cannot be empty")
        if self.weekly_growth < 0:
            raise ValueError("weekly growth cannot be negative")
        unit_sids = (self.base_sid, self.upgrade_option_1_sid, self.upgrade_option_2_sid)
        if any(not sid for sid in unit_sids):
            raise ValueError("all three unit SIDs must be present")
        if len(set(unit_sids)) != 3:
            raise ValueError("base and upgrade option SIDs must be distinct")


@dataclass(frozen=True, slots=True)
class BuildingLevel:
    key: BuildingKey
    category: str
    name_key: str | None
    scene_slot: str | None
    cost: ResourceCost
    prerequisites: tuple[BuildingKey, ...] = ()
    constructed_on_start: bool = False
    unit_family: UnitFamily | None = None
    node_x: int | None = None
    node_y: int | None = None
    income: ResourceCost = field(default_factory=ResourceCost)

    def __post_init__(self) -> None:
        if not self.category:
            raise ValueError("building category cannot be empty")
        if len(set(self.prerequisites)) != len(self.prerequisites):
            raise ValueError(f"Duplicate prerequisites for {self.key}")
        for prerequisite in self.prerequisites:
            if prerequisite.faction != self.key.faction:
                raise ValueError(f"Cross-faction prerequisites are not supported: {self.key} -> {prerequisite}")
        if self.unit_family and self.unit_family.faction != self.key.faction:
            raise ValueError("Unit family faction does not match building faction")
        if any(value < 0 for value in self.income.as_dict().values()):
            raise ValueError(f"Building income cannot be negative: {self.key}")


@dataclass(slots=True)
class FactionCity:
    faction: str
    city_id: str
    buildings: dict[BuildingKey, BuildingLevel] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.faction:
            raise ValueError("faction cannot be empty")
        if not self.city_id:
            raise ValueError("city_id cannot be empty")

    def add_building(self, building: BuildingLevel) -> None:
        if building.key.faction != self.faction:
            raise ValueError(f"Cannot add {building.key.faction!r} building to {self.faction!r} city")
        if building.key in self.buildings:
            raise ValueError(f"Duplicate building node: {building.key}")
        self.buildings[building.key] = building

    def get(self, sid: str, level: int) -> BuildingLevel:
        key = BuildingKey(self.faction, sid, level)
        try:
            return self.buildings[key]
        except KeyError as exc:
            raise KeyError(f"Unknown building node: {key}") from exc


@dataclass(slots=True)
class GameDatabase:
    cities: dict[str, FactionCity] = field(default_factory=dict)

    def add_city(self, city: FactionCity) -> None:
        if city.faction in self.cities:
            raise ValueError(f"Duplicate faction city: {city.faction}")
        self.cities[city.faction] = city

    def city(self, faction: str) -> FactionCity:
        try:
            return self.cities[faction]
        except KeyError as exc:
            raise KeyError(f"Unknown faction: {faction!r}") from exc
