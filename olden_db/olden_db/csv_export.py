from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

from .constants import RESOURCE_NAMES
from .database import LoadedGameData
from .graph import build_dependency_graph, iter_topological_orders
from .models import BuildingLevel, ResourceCost
from .planner import BuildPlan, plan_build_order


@dataclass(frozen=True, slots=True)
class ValidationExportPaths:
    """Paths created by one validation export run."""

    buildings: Path
    units: Path
    dependency_graph: Path
    representative_plan: Path


def export_validation_csvs(
    data: LoadedGameData,
    output_directory: str | Path,
) -> ValidationExportPaths:
    """Export deterministic CSV snapshots of the connected backend data."""
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)

    paths = ValidationExportPaths(
        buildings=output / "buildings.csv",
        units=output / "units.csv",
        dependency_graph=output / "building_dependency_graph.csv",
        representative_plan=output / "representative_plan.csv",
    )

    _write_buildings(data, paths.buildings)
    _write_units(data, paths.units)
    _write_dependency_graph(data, paths.dependency_graph)
    _write_plan(_representative_plan(data), paths.representative_plan)

    return paths


def _write_buildings(data: LoadedGameData, path: Path) -> None:
    fieldnames = [
        "faction", "sid", "level", "category", "name_key", "scene_slot",
        "constructed_on_start", "node_x", "node_y", "unit_tier",
        "unit_base_sid", "unit_upgrade_option_1_sid",
        "unit_upgrade_option_2_sid", "weekly_growth", *RESOURCE_NAMES,
    ]

    rows: list[dict[str, object]] = []
    for building in _sorted_buildings(data):
        family = building.unit_family
        row: dict[str, object] = {
            "faction": building.key.faction,
            "sid": building.key.sid,
            "level": building.key.level,
            "category": building.category,
            "name_key": building.name_key or "",
            "scene_slot": building.scene_slot or "",
            "constructed_on_start": building.constructed_on_start,
            "node_x": "" if building.node_x is None else building.node_x,
            "node_y": "" if building.node_y is None else building.node_y,
            "unit_tier": "" if family is None else family.tier,
            "unit_base_sid": "" if family is None else family.base_sid,
            "unit_upgrade_option_1_sid": "" if family is None else family.upgrade_option_1_sid,
            "unit_upgrade_option_2_sid": "" if family is None else family.upgrade_option_2_sid,
            "weekly_growth": "" if family is None else family.weekly_growth,
        }
        row.update(building.cost.as_dict())
        rows.append(row)

    _write_rows(path, fieldnames, rows)


def _write_units(data: LoadedGameData, path: Path) -> None:
    fieldnames = ["sid", "faction", "tier", "upgrade_sid", "source", *RESOURCE_NAMES]
    rows: list[dict[str, object]] = []

    for unit in sorted(
        data.units.units.values(),
        key=lambda item: (item.faction, item.tier, item.sid),
    ):
        row: dict[str, object] = {
            "sid": unit.sid,
            "faction": unit.faction,
            "tier": unit.tier,
            "upgrade_sid": unit.upgrade_sid or "",
            "source": _normalize_unit_source(unit.source),
        }
        row.update(unit.cost.as_dict())
        rows.append(row)

    _write_rows(path, fieldnames, rows)


def _normalize_unit_source(source: str) -> str:
    """Return a stable logical asset path for a parsed unit source."""
    archive_path, separator, member_path = source.partition("!")
    normalized_archive = _logical_asset_path(archive_path)

    if not separator:
        return normalized_archive

    normalized_member = str(PurePosixPath(member_path.replace("\\", "/")))
    return f"{normalized_archive}!{normalized_member}"


def _logical_asset_path(raw_path: str) -> str:
    """Remove machine-specific parents while retaining the game asset path."""
    path = PurePosixPath(raw_path.replace("\\", "/"))
    parts = path.parts

    for anchor in ("Core", "units_logics"):
        if anchor in parts:
            return str(PurePosixPath(*parts[parts.index(anchor):]))

    return path.name


def _write_dependency_graph(data: LoadedGameData, path: Path) -> None:
    fieldnames = ["faction", "sid", "level", "prerequisite_sid", "prerequisite_level"]
    rows: list[dict[str, object]] = []

    for building in _sorted_buildings(data):
        prerequisites = sorted(building.prerequisites, key=lambda key: (key.sid, key.level))
        if not prerequisites:
            rows.append({
                "faction": building.key.faction,
                "sid": building.key.sid,
                "level": building.key.level,
                "prerequisite_sid": "",
                "prerequisite_level": "",
            })
            continue

        for prerequisite in prerequisites:
            rows.append({
                "faction": building.key.faction,
                "sid": building.key.sid,
                "level": building.key.level,
                "prerequisite_sid": prerequisite.sid,
                "prerequisite_level": prerequisite.level,
            })

    _write_rows(path, fieldnames, rows)


def _write_plan(plan: BuildPlan, path: Path) -> None:
    fieldnames = [
        "faction", "target_sid", "target_level", "order_number",
        "step_number", "date", "building_sid", "building_level",
        *(f"individual_{name}" for name in RESOURCE_NAMES),
        *(f"cumulative_{name}" for name in RESOURCE_NAMES),
    ]
    rows: list[dict[str, object]] = []

    for step in plan.steps:
        row: dict[str, object] = {
            "faction": plan.faction,
            "target_sid": plan.target.sid,
            "target_level": plan.target.level,
            "order_number": plan.order_number,
            "step_number": step.step_number,
            "date": step.date.code,
            "building_sid": step.building.sid,
            "building_level": step.building.level,
        }
        row.update(_prefixed_cost("individual", step.individual_cost))
        row.update(_prefixed_cost("cumulative", step.cumulative_cost))
        rows.append(row)

    _write_rows(path, fieldnames, rows)


def _representative_plan(data: LoadedGameData) -> BuildPlan:
    candidates = []
    for faction in sorted(data.cities.cities):
        city = data.cities.city(faction)
        for key in sorted(city.buildings):
            graph = build_dependency_graph(city, key)
            candidates.append((graph.build_actions, key, city, graph))

    if not candidates:
        raise ValueError("Cannot export a representative plan from an empty database")

    _, _, city, graph = max(
        candidates,
        key=lambda item: (item[0], item[1].faction, item[1].sid, item[1].level),
    )
    order = next(iter_topological_orders(graph))
    return plan_build_order(city, graph, order)


def _sorted_buildings(data: LoadedGameData) -> tuple[BuildingLevel, ...]:
    return tuple(sorted(
        (
            building
            for city in data.cities.cities.values()
            for building in city.buildings.values()
        ),
        key=lambda building: (
            building.key.faction,
            building.key.sid,
            building.key.level,
        ),
    ))


def _prefixed_cost(prefix: str, cost: ResourceCost) -> dict[str, int]:
    return {f"{prefix}_{name}": amount for name, amount in cost.as_dict().items()}


def _write_rows(
    path: Path,
    fieldnames: list[str],
    rows: Iterable[dict[str, object]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
