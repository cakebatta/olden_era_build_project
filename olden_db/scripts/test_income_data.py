from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from olden_db.database import PLAYABLE_FACTIONS
from olden_db.paths import require_city_directory


INCOME_EFFECT_TYPE = "sideRes"
BASELINE_CONTAINER = "bonusesPerLevel"
OPTIONAL_CONTAINER = "optionalEffectsPerLevel"
FREQUENCY_KEYS = frozenset(
    {
        "frequency",
        "period",
        "interval",
        "daily",
        "weekly",
        "perDay",
        "perWeek",
        "day",
        "week",
        "startDay",
        "activationDelay",
        "constructionDay",
    }
)


@dataclass(frozen=True, slots=True, order=True)
class IncomeEffect:
    faction: str
    building_sid: str
    level: int
    source_kind: str
    effect_sid: str
    resource: str
    amount: int
    source_file: str


class IncomeDataError(ValueError):
    """Raised when canonical income data is malformed or inconsistent."""


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise IncomeDataError(
            f"Invalid JSON in {path}: line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc


def _iter_buildings(city_record: dict[str, object]) -> Iterable[dict[str, object]]:
    for value in city_record.values():
        if not isinstance(value, list):
            continue
        for item in value:
            if (
                isinstance(item, dict)
                and isinstance(item.get("sid"), str)
                and isinstance(item.get("parametersPerLevel"), list)
            ):
                yield item


def _iter_bonus_objects(value: object) -> Iterable[dict[str, object]]:
    if isinstance(value, dict):
        if isinstance(value.get("type"), str):
            yield value
        for nested in value.values():
            yield from _iter_bonus_objects(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _iter_bonus_objects(nested)


def _parse_side_res(
    bonus: dict[str, object],
    *,
    faction: str,
    building_sid: str,
    level: int,
    source_kind: str,
    source_file: Path,
) -> IncomeEffect:
    parameters = bonus.get("parameters")
    if not isinstance(parameters, list) or len(parameters) < 2:
        raise IncomeDataError(
            f"{source_file}: {faction}/{building_sid} level {level} "
            f"contains malformed {INCOME_EFFECT_TYPE!r} parameters: "
            f"{parameters!r}"
        )

    resource = str(parameters[0]).strip()
    if not resource:
        raise IncomeDataError(
            f"{source_file}: {faction}/{building_sid} level {level} "
            "contains an empty income resource"
        )

    try:
        amount = int(parameters[1])
    except (TypeError, ValueError) as exc:
        raise IncomeDataError(
            f"{source_file}: {faction}/{building_sid} level {level} "
            f"contains invalid income amount: {parameters[1]!r}"
        ) from exc

    if amount <= 0:
        raise IncomeDataError(
            f"{source_file}: {faction}/{building_sid} level {level} "
            f"contains non-positive income: {resource}={amount}"
        )

    effect_sid = str(bonus.get("sid", "")).strip()

    return IncomeEffect(
        faction=faction,
        building_sid=building_sid,
        level=level,
        source_kind=source_kind,
        effect_sid=effect_sid,
        resource=resource,
        amount=amount,
        source_file=source_file.name,
    )


def _scan_container(
    levels: object,
    *,
    faction: str,
    building_sid: str,
    source_kind: str,
    source_file: Path,
) -> list[IncomeEffect]:
    if levels is None:
        return []
    if not isinstance(levels, list):
        raise IncomeDataError(
            f"{source_file}: {faction}/{building_sid}.{source_kind} "
            "must be a list"
        )

    effects: list[IncomeEffect] = []
    for index, level_data in enumerate(levels, start=1):
        for bonus in _iter_bonus_objects(level_data):
            if bonus.get("type") != INCOME_EFFECT_TYPE:
                continue
            effects.append(
                _parse_side_res(
                    bonus,
                    faction=faction,
                    building_sid=building_sid,
                    level=index,
                    source_kind=source_kind,
                    source_file=source_file,
                )
            )
    return effects


def _find_frequency_metadata(value: object, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            nested_path = f"{path}.{key}" if path else key
            if key in FREQUENCY_KEYS:
                findings.append(f"{nested_path}={nested!r}")
            findings.extend(_find_frequency_metadata(nested, nested_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            findings.extend(
                _find_frequency_metadata(nested, f"{path}[{index}]")
            )
    return findings


def _format_effect(effect: IncomeEffect) -> str:
    label = (
        f"{effect.building_sid} level {effect.level}: "
        f"{effect.resource} +{effect.amount}"
    )
    if effect.effect_sid:
        label += f" (effect {effect.effect_sid})"
    return label


def main() -> None:
    city_directory = require_city_directory()
    paths = sorted(city_directory.glob("*_city.json"))
    if not paths:
        raise FileNotFoundError(
            f"No canonical city files were found in {city_directory}"
        )

    baseline: list[IncomeEffect] = []
    optional: list[IncomeEffect] = []
    frequency_metadata: list[str] = []
    discovered_factions: set[str] = set()

    for path in paths:
        data = _load_json(path)
        raw_cities = data.get("array") if isinstance(data, dict) else None
        if not isinstance(raw_cities, list) or len(raw_cities) != 1:
            raise IncomeDataError(
                f"{path} must contain exactly one city in top-level 'array'"
            )

        city = raw_cities[0]
        if not isinstance(city, dict):
            raise IncomeDataError(f"{path}: city entry must be an object")

        faction = city.get("fraction")
        if not isinstance(faction, str) or not faction:
            raise IncomeDataError(f"{path}: city faction is missing")
        discovered_factions.add(faction)

        for building in _iter_buildings(city):
            building_sid = str(building["sid"])
            baseline.extend(
                _scan_container(
                    building.get(BASELINE_CONTAINER),
                    faction=faction,
                    building_sid=building_sid,
                    source_kind="baseline",
                    source_file=path,
                )
            )
            optional.extend(
                _scan_container(
                    building.get(OPTIONAL_CONTAINER),
                    faction=faction,
                    building_sid=building_sid,
                    source_kind="optional",
                    source_file=path,
                )
            )

        for finding in _find_frequency_metadata(city):
            frequency_metadata.append(f"{path.name}: {finding}")

    missing_factions = sorted(set(PLAYABLE_FACTIONS) - discovered_factions)
    if missing_factions:
        raise IncomeDataError(
            f"Missing playable faction city assets: {missing_factions}"
        )

    unexpected_factions = sorted(discovered_factions - set(PLAYABLE_FACTIONS))

    all_effects = sorted(baseline + optional)
    if len(set(all_effects)) != len(all_effects):
        raise IncomeDataError("Duplicate income effects were discovered")

    print("Town income data validation")
    print(f"Playable factions: {len(PLAYABLE_FACTIONS)}")
    print(f"Baseline income effects: {len(baseline)}")
    print(f"Optional income effects: {len(optional)}")
    print()

    for faction in PLAYABLE_FACTIONS:
        faction_baseline = sorted(
            effect for effect in baseline if effect.faction == faction
        )
        faction_optional = sorted(
            effect for effect in optional if effect.faction == faction
        )

        print(f"{faction}:")
        print("  Baseline income:")
        if faction_baseline:
            for effect in faction_baseline:
                print(f"    {_format_effect(effect)}")
        else:
            print("    None")

        print("  Optional income choices:")
        if faction_optional:
            for effect in faction_optional:
                print(f"    {_format_effect(effect)}")
        else:
            print("    None")
        print()

    print("Frequency and activation metadata:")
    if frequency_metadata:
        for finding in frequency_metadata:
            print(f"  FOUND: {finding}")
    else:
        print("  None encoded in the inspected city bonus structures.")
        print("  Daily/weekly frequency is not authoritative asset data here.")
        print("  Construction-day activation timing is not encoded here.")

    print()
    print("Parser coverage:")
    print("  INCOMPLETE for town income.")
    print(
        "  BuildingLevel does not retain bonusesPerLevel, "
        "optionalEffectsPerLevel, or normalized income effects."
    )
    print(
        "  Raw assets contain resource and amount data, but current parsed "
        "data cannot supply it to deterministic gameplay."
    )

    print()
    print("Faction-specific exceptions:")
    if unexpected_factions:
        print(
            "  Non-playable city assets also discovered: "
            + ", ".join(unexpected_factions)
        )
    else:
        print("  No unexpected faction assets discovered.")
    print(
        "  Review the per-faction baseline and optional lists above for "
        "content differences; no timing exception is encoded."
    )

    print()
    print("PASS")
    print("  All playable faction city assets were inspected.")
    print("  All sideRes entries have valid resources and positive amounts.")
    print("  Baseline and optional income effects are reported separately.")
    print("  Missing frequency and activation timing are reported explicitly.")
    print("  Current parser incompleteness is reported without modifying it.")


if __name__ == "__main__":
    main()
