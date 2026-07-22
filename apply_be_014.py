from __future__ import annotations

import ast
import subprocess
from pathlib import Path

EXPECTED = "cb62414eaff8ced20cb74ec35e90f4a087bec747"
ROOT = Path(__file__).resolve().parent
QUERY = ROOT / "olden_db" / "olden_db" / "query.py"
PATHS = ROOT / "olden_db" / "olden_db" / "paths.py"
PLANNER_LOCALIZATION = ROOT / "olden_db" / "olden_db" / "planner_localization.py"
TEST = ROOT / "olden_db" / "scripts" / "test_planner_localization_catalog.py"
REPORT = ROOT / "docs" / "BE-014-IMPLEMENTATION-REPORT.md"
RUNTIME = ROOT / "docs" / "be014_runtime_verification.md"
QUERY_DOC = ROOT / "docs" / "query_layer.md"
ARCH_DOC = ROOT / "docs" / "planner_localization_architecture.md"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"SKIP: {label}")
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one reviewed anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"UPDATED: {label}")


def require_packaged_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing packaged file: {path}")
    print(f"FOUND: {path.relative_to(ROOT)}")


def patch_paths() -> None:
    anchor = '''def require_english_cities_localization_file() -> Path:
    """Return the English city/building localization file."""
    if not ENGLISH_CITIES_LOCALIZATION_FILE.is_file():
        raise FileNotFoundError(
            "English city localization file was not found. Expected:\\n"
            f"  {ENGLISH_CITIES_LOCALIZATION_FILE}"
        )
    return ENGLISH_CITIES_LOCALIZATION_FILE
'''
    replacement = anchor + '''

def require_english_planner_localization_file() -> Path:
    """Return the explicit English planner-localization source document."""
    return require_english_cities_localization_file()
'''
    replace_once(PATHS, anchor, replacement, "explicit planner localization path")


def patch_query() -> None:
    replace_once(QUERY, "from .localization import LocalizationCatalog, parse_localization_directory\n", "from .localization import parse_localization_file\n", "localization import")
    replace_once(
        QUERY,
        "from .paths import require_english_localization_directory\n",
        "from .paths import require_english_planner_localization_file\nfrom .planner_localization import (\n    PlannerLocalizationCatalog,\n    build_planner_localization_catalog,\n)\n",
        "planner localization imports",
    )
    replace_once(
        QUERY,
        '''class UnknownBuildingError(QueryError):
    """Raised when a requested building level is not present."""


''',
        '''class UnknownBuildingError(QueryError):
    """Raised when a requested building level is not present."""


class UnknownUnitError(QueryError):
    """Raised when a requested unit identity is not present."""


''',
        "unknown unit error",
    )
    replace_once(QUERY, "    _localization: LocalizationCatalog | None = None\n", "    _planner_localization: PlannerLocalizationCatalog | None = None\n", "catalog field")
    replace_once(
        QUERY,
        '''        return cls(
            load_default_game_data(),
            parse_localization_directory(
                require_english_localization_directory(),
                language="english",
            ),
        )
''',
        '''        data = load_default_game_data()
        localization = parse_localization_file(
            require_english_planner_localization_file(),
            language="english",
        )
        return cls(
            data,
            build_planner_localization_catalog(data, localization),
        )
''',
        "eager planner catalog construction",
    )
    replace_once(
        QUERY,
        '''    def get_faction_display_text(self, faction: str) -> str:
        city = self._get_city(faction)
        if self._localization is None:
            return faction
        for candidate in (city.city_id, faction):
            if candidate and self._localization.contains(candidate):
                return self._localization.get(candidate)
        return faction

    def get_unit_display_text(self, unit_sid: str) -> str:
        definition = self._data.units.get(unit_sid)
        if self._localization is None:
            return definition.sid
        return self._localization.resolve(definition.sid, fallback=definition.sid) or definition.sid

''',
        '''    def get_faction_display_name(self, faction: str) -> str:
        self._get_city(faction)
        if self._planner_localization is None:
            return faction
        return self._planner_localization.get_faction_display_name(faction)

    def get_faction_display_text(self, faction: str) -> str:
        """Compatibility alias for the planner faction display-name operation."""
        return self.get_faction_display_name(faction)

    def get_unit_display_name(self, faction: str, unit_sid: str) -> str:
        definition = self._get_unit(faction, unit_sid)
        if self._planner_localization is None:
            return definition.sid
        return self._planner_localization.get_unit_display_name(faction, unit_sid)

    def get_unit_display_text(self, faction_or_unit_sid: str, unit_sid: str | None = None) -> str:
        """Return a unit display name while preserving the legacy one-argument form."""
        if unit_sid is None:
            definition = self._get_unit_by_sid(faction_or_unit_sid)
            return self.get_unit_display_name(definition.faction, definition.sid)
        return self.get_unit_display_name(faction_or_unit_sid, unit_sid)

    def get_upgrade_display_name(self, faction: str, upgrade_sid: str) -> str:
        definition = self._get_unit(faction, upgrade_sid)
        if self._planner_localization is None:
            return definition.sid
        try:
            return self._planner_localization.get_upgrade_display_name(faction, upgrade_sid)
        except KeyError:
            return self._planner_localization.get_unit_display_name(faction, upgrade_sid)

    def get_upgrade_display_text(self, faction: str, upgrade_sid: str) -> str:
        return self.get_upgrade_display_name(faction, upgrade_sid)

''',
        "faction unit upgrade APIs",
    )
    replace_once(
        QUERY,
        '''    def get_building_display_text(self, building: BuildingKey) -> str:
        """
        Return localized display text for one canonical building identity.

        Localization remains a Query Layer responsibility. Application clients
        must not read localization catalogs or repository paths directly.
        """
        if not isinstance(building, BuildingKey):
            raise TypeError("building must be a BuildingKey")
        definition = self.get_building(
            building.faction,
            building.sid,
            building.level,
        )
        fallback = definition.name_key or building.sid
        if self._localization is None:
            return fallback
        return self._localization.resolve(
            definition.name_key,
            fallback=fallback,
        ) or fallback
''',
        '''    def get_building_display_name(self, building: BuildingKey) -> str:
        """Return planner-facing text without changing canonical BuildingKey identity."""
        if not isinstance(building, BuildingKey):
            raise TypeError("building must be a BuildingKey")
        self.get_building(building.faction, building.sid, building.level)
        if self._planner_localization is None:
            return building.sid
        return self._planner_localization.get_building_display_name(building)

    def get_building_display_text(self, building: BuildingKey) -> str:
        """Compatibility alias for the planner building display-name operation."""
        return self.get_building_display_name(building)
''',
        "building catalog delegation",
    )
    anchor = '''    def _get_city(self, faction: str) -> FactionCity:
        if not faction:
            raise QueryError("faction cannot be empty")
        try:
            return self._data.cities.city(faction)
        except KeyError as exc:
            raise UnknownFactionError(f"Unknown faction: {faction!r}") from exc

'''
    replacement = anchor + '''    def _get_unit_by_sid(self, unit_sid: str):
        if not unit_sid:
            raise QueryError("unit_sid cannot be empty")
        try:
            return self._data.units.get(unit_sid)
        except KeyError as exc:
            raise UnknownUnitError(f"Unknown unit SID: {unit_sid!r}") from exc

    def _get_unit(self, faction: str, unit_sid: str):
        self._get_city(faction)
        definition = self._get_unit_by_sid(unit_sid)
        if definition.faction != faction:
            raise UnknownUnitError(
                f"Unknown unit for faction: faction={faction!r}, unit_sid={unit_sid!r}"
            )
        return definition

'''
    replace_once(QUERY, anchor, replacement, "unit validation helpers")


def patch_docs() -> None:
    query_section = '''

## BE-014 Planner Localization Catalog Implementation

Canonical startup parses one explicit planner-localization source document and constructs one immutable `PlannerLocalizationCatalog`. The builder enumerates only planner-visible canonical factions, buildings, units, and upgrades from `LoadedGameData`; unrelated interface tokens are not copied into planner indexes.

Public display-name operations are `get_faction_display_name(...)`, `get_building_display_name(...)`, `get_unit_display_name(...)`, and `get_upgrade_display_name(...)`. Existing display-text operations remain compatible and delegate to the catalog.
'''
    arch_section = '''

## BE-014 Realization

BE-014 realizes this architecture with `planner_localization.py`. Canonical startup uses the explicit English `cities.json` planner source rather than directory parsing. Existing parser duplicate semantics are unchanged. Temporary dictionaries exist only during construction; the published catalog uses immutable mappings and performs no lookup-time I/O or mutation.
'''
    for path, section, marker in ((QUERY_DOC, query_section, "## BE-014 Planner Localization Catalog Implementation"), (ARCH_DOC, arch_section, "## BE-014 Realization")):
        text = path.read_text(encoding="utf-8")
        if marker not in text:
            path.write_text(text.rstrip() + section + "\n", encoding="utf-8")
            print(f"UPDATED: {path.relative_to(ROOT)}")
        else:
            print(f"SKIP: {path.relative_to(ROOT)} documentation")


def validate() -> None:
    for path in (PLANNER_LOCALIZATION, QUERY, PATHS, TEST):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print(f"PASS: syntax {path.relative_to(ROOT)}")


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != EXPECTED:
        raise RuntimeError(f"Expected HEAD {EXPECTED}; found {head}. Apply BE-014 only to the authorized ARCH-021 baseline.")
    for path in (PLANNER_LOCALIZATION, TEST, REPORT, RUNTIME):
        require_packaged_file(path)
    patch_paths()
    patch_query()
    patch_docs()
    validate()
    print("BE-014 applied successfully.")


if __name__ == "__main__":
    main()
