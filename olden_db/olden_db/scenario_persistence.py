from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Callable
from uuid import UUID, uuid4

from .database import LoadedGameData
from .models import BuildingKey, ResourceCost
from .planner import GameDate
from .resource_ledger import RecruitmentAction
from .scenario import PlanningScenario, StartingBuildingOverride

SCENARIO_SCHEMA_VERSION = 1
MAX_SCENARIO_FILE_SIZE = 1024 * 1024
MAX_JSON_NESTING_DEPTH = 32
RESOURCE_NAMES = ("gold", "wood", "ore", "gemstones", "crystals", "mercury", "dust", "graal")
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class ScenarioPersistenceError(Exception):
    pass


class ScenarioSerializationError(ScenarioPersistenceError):
    pass


class ScenarioDocumentValidationError(ScenarioPersistenceError, ValueError):
    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.detail = message
        super().__init__(f"{path}: {message}" if path else message)


class UnsupportedScenarioVersionError(ScenarioPersistenceError):
    pass


class ScenarioNotFoundError(ScenarioPersistenceError):
    pass


class ScenarioConflictError(ScenarioPersistenceError):
    pass


class ScenarioStorageError(ScenarioPersistenceError):
    pass


@dataclass(frozen=True, slots=True)
class ScenarioDocument:
    schema_version: int
    scenario_id: UUID
    name: str
    description: str
    created_at: datetime
    modified_at: datetime
    faction: str
    target: BuildingKey
    starting_date: GameDate
    planning_scenario: PlanningScenario
    starting_resources: ResourceCost
    recruitment_actions: tuple[RecruitmentAction, ...]
    notes: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ScenarioDocumentValidationError("schema_version", "must be the integer 1")
        if not isinstance(self.scenario_id, UUID):
            raise ScenarioDocumentValidationError("scenario_id", "must be a UUID")
        if not isinstance(self.name, str):
            raise ScenarioDocumentValidationError("name", "must be a string")
        name = self.name.strip()
        if not name:
            raise ScenarioDocumentValidationError("name", "cannot be blank")
        if len(name) > 120:
            raise ScenarioDocumentValidationError("name", "must contain at most 120 Unicode code points")
        object.__setattr__(self, "name", name)
        _validate_text(self.description, "description", 500)
        _validate_text(self.notes, "notes", 20_000)
        created = _require_utc(self.created_at, "created_at")
        modified = _require_utc(self.modified_at, "modified_at")
        if modified < created:
            raise ScenarioDocumentValidationError("modified_at", "cannot be earlier than created_at")
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "modified_at", modified)
        if not isinstance(self.faction, str) or not self.faction.strip():
            raise ScenarioDocumentValidationError("game_context.faction", "must be a nonblank string")
        if not isinstance(self.target, BuildingKey) or self.target.faction != self.faction:
            raise ScenarioDocumentValidationError("game_context.target", "must be a BuildingKey for the document faction")
        if not isinstance(self.starting_date, GameDate):
            raise ScenarioDocumentValidationError("game_context.starting_date", "must be a GameDate")
        if not isinstance(self.planning_scenario, PlanningScenario):
            raise ScenarioDocumentValidationError("planning_scenario", "must be a PlanningScenario")
        if not isinstance(self.starting_resources, ResourceCost):
            raise ScenarioDocumentValidationError("starting_resources", "must be a ResourceCost")
        for resource in RESOURCE_NAMES:
            value = getattr(self.starting_resources, resource)
            if type(value) is not int or value < 0:
                raise ScenarioDocumentValidationError(f"starting_resources.{resource}", "must be a nonnegative integer")
        actions = tuple(self.recruitment_actions)
        for i, action in enumerate(actions):
            if not isinstance(action, RecruitmentAction):
                raise ScenarioDocumentValidationError(f"recruitment_actions[{i}]", "must be a RecruitmentAction")
            if action.dwelling.faction != self.faction:
                raise ScenarioDocumentValidationError(f"recruitment_actions[{i}].dwelling", "faction must match document faction")
        if len(actions) != len(set(actions)):
            raise ScenarioDocumentValidationError("recruitment_actions", "exact duplicate actions are not allowed")
        object.__setattr__(self, "recruitment_actions", tuple(sorted(actions, key=_action_key)))
        for i, override in enumerate(self.planning_scenario.starting_building_overrides):
            if override.building.faction != self.faction:
                raise ScenarioDocumentValidationError(f"planning_scenario.starting_building_overrides[{i}]", "faction must match document faction")


@dataclass(frozen=True, slots=True)
class ScenarioLoadResult:
    document: ScenarioDocument
    conflict_token: str


@dataclass(frozen=True, slots=True)
class ScenarioSaveResult:
    document: ScenarioDocument
    conflict_token: str


@dataclass(frozen=True, slots=True)
class ScenarioSummary:
    scenario_id: UUID
    name: str
    description: str
    modified_at: datetime
    faction: str
    target: BuildingKey


@dataclass(frozen=True, slots=True)
class ScenarioEntryDiagnostic:
    filename: str
    category: str
    message: str


@dataclass(frozen=True, slots=True)
class ScenarioRepositoryListing:
    scenarios: tuple[ScenarioSummary, ...]
    diagnostics: tuple[ScenarioEntryDiagnostic, ...]


def create_scenario_document(*, name: str, faction: str, target_sid: str, target_level: int,
                             now: datetime, scenario_id_factory: Callable[[], UUID] = uuid4,
                             description: str = "", starting_date: GameDate = GameDate(1, 1, 1),
                             planning_scenario: PlanningScenario = PlanningScenario(),
                             starting_resources: ResourceCost = ResourceCost(),
                             recruitment_actions: tuple[RecruitmentAction, ...] = (), notes: str = "") -> ScenarioDocument:
    timestamp = _require_utc(now, "now")
    return ScenarioDocument(1, scenario_id_factory(), name, description, timestamp, timestamp,
                            faction, BuildingKey(faction, target_sid, target_level), starting_date,
                            planning_scenario, starting_resources, recruitment_actions, notes)


def duplicate_scenario_document(document: ScenarioDocument, *, now: datetime, name: str | None = None,
                                scenario_id_factory: Callable[[], UUID] = uuid4) -> ScenarioDocument:
    _require_document(document)
    timestamp = _require_utc(now, "now")
    return replace(document, scenario_id=scenario_id_factory(), name=document.name if name is None else name,
                   created_at=timestamp, modified_at=timestamp)


def rename_scenario_document(document: ScenarioDocument, name: str) -> ScenarioDocument:
    _require_document(document)
    return replace(document, name=name)


def serialize_scenario_document(document: ScenarioDocument) -> str:
    _require_document(document)
    try:
        return json.dumps(_to_object(document), ensure_ascii=False, allow_nan=False, indent=2,
                          separators=(",", ": ")) + "\n"
    except (TypeError, ValueError) as exc:
        raise ScenarioSerializationError("Unable to serialize scenario document") from exc


def serialize_scenario_document_bytes(document: ScenarioDocument) -> bytes:
    return serialize_scenario_document(document).encode("utf-8")


def deserialize_scenario_document(data: str | bytes) -> ScenarioDocument:
    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ScenarioSerializationError("Scenario document is not valid UTF-8") from exc
    elif isinstance(data, str):
        text = data
    else:
        raise TypeError("data must be str or bytes")
    if len(text.encode("utf-8")) > MAX_SCENARIO_FILE_SIZE:
        raise ScenarioDocumentValidationError("", f"document exceeds {MAX_SCENARIO_FILE_SIZE} bytes")
    try:
        raw = json.loads(text, object_pairs_hook=_pairs)
    except ScenarioDocumentValidationError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise ScenarioSerializationError("Malformed scenario JSON") from exc
    if not isinstance(raw, dict):
        raise ScenarioDocumentValidationError("", "top-level JSON must be an object")
    _depth(raw)
    if "schema_version" not in raw:
        raise ScenarioDocumentValidationError("schema_version", "required field is missing")
    version = raw["schema_version"]
    if type(version) is not int:
        raise ScenarioDocumentValidationError("schema_version", "must be an integer")
    if version != 1:
        raise UnsupportedScenarioVersionError(f"Unsupported scenario schema version: {version}")
    return _from_v1(raw)


def validate_document_against_game_data(document: ScenarioDocument, database: LoadedGameData) -> None:
    _require_document(document)
    if not isinstance(database, LoadedGameData):
        raise TypeError("database must be LoadedGameData")
    try:
        city = database.cities.city(document.faction)
    except KeyError as exc:
        raise ScenarioDocumentValidationError("game_context.faction", f"unknown faction {document.faction!r}") from exc
    if document.target not in city.buildings:
        same_sid = any(key.sid == document.target.sid for key in city.buildings)
        path = "game_context.target.level" if same_sid else "game_context.target.sid"
        raise ScenarioDocumentValidationError(path, f"unknown target {document.target.sid!r} level {document.target.level}")
    for i, override in enumerate(document.planning_scenario.starting_building_overrides):
        path = f"planning_scenario.starting_building_overrides[{i}]"
        building = city.buildings.get(override.building)
        if building is None:
            raise ScenarioDocumentValidationError(f"{path}.sid", "unknown scenario building")
        if building.constructed_on_start == override.available_at_start:
            raise ScenarioDocumentValidationError(path, "override does not change the canonical starting state")
    for i, action in enumerate(document.recruitment_actions):
        path = f"recruitment_actions[{i}].dwelling"
        building = city.buildings.get(action.dwelling)
        if building is None:
            raise ScenarioDocumentValidationError(f"{path}.sid", "unknown recruitment dwelling")
        if building.unit_family is None:
            raise ScenarioDocumentValidationError(path, "referenced building is not a recruitment dwelling")


class LocalScenarioRepository:
    def __init__(self, root: str | Path, *, canonical_validator: Callable[[ScenarioDocument], None] | None = None) -> None:
        self._root = Path(root)
        self._scenario_dir = self._root / "scenarios"
        self._canonical_validator = canonical_validator

    @property
    def root(self) -> Path:
        return self._root

    @property
    def scenario_directory(self) -> Path:
        return self._scenario_dir

    def list_scenarios(self) -> ScenarioRepositoryListing:
        self._ensure_dir()
        summaries, diagnostics = [], []
        try:
            entries = tuple(self._scenario_dir.iterdir())
        except OSError as exc:
            raise ScenarioStorageError("Unable to list scenario repository") from exc
        for entry in sorted(entries, key=lambda p: p.name):
            if not entry.is_file() or entry.is_symlink():
                if entry.name.endswith(".json"):
                    diagnostics.append(ScenarioEntryDiagnostic(entry.name, "unsafe_entry", "not a regular non-symlink file"))
                continue
            if not _canonical_filename(entry.name):
                diagnostics.append(ScenarioEntryDiagnostic(entry.name, "invalid_filename", "filename must be canonical UUID plus .json"))
                continue
            try:
                data = self._read(entry)
                document = deserialize_scenario_document(data)
                if document.scenario_id != UUID(entry.stem):
                    raise ScenarioDocumentValidationError("scenario_id", "UUID does not match managed filename")
                summaries.append(ScenarioSummary(document.scenario_id, document.name, document.description,
                                                 document.modified_at, document.faction, document.target))
            except ScenarioPersistenceError as exc:
                diagnostics.append(ScenarioEntryDiagnostic(entry.name, type(exc).__name__, str(exc)))
        summaries.sort(key=lambda s: (s.name.casefold(), s.name, str(s.scenario_id)))
        return ScenarioRepositoryListing(tuple(summaries), tuple(diagnostics))

    def get_scenario(self, scenario_id: UUID | str) -> ScenarioLoadResult:
        identifier = _uuid(scenario_id)
        path = self._path(identifier)
        if not path.exists():
            raise ScenarioNotFoundError(f"Scenario not found: {identifier}")
        self._no_symlink(path)
        data = self._read(path)
        document = deserialize_scenario_document(data)
        if document.scenario_id != identifier:
            raise ScenarioDocumentValidationError("scenario_id", "UUID does not match managed filename")
        return ScenarioLoadResult(document, _token(data))

    def save_scenario(self, document: ScenarioDocument, *, expected_token: str | None, now: datetime) -> ScenarioSaveResult:
        _require_document(document)
        timestamp = _require_utc(now, "now")
        if self._canonical_validator:
            self._canonical_validator(document)
        path = self._path(document.scenario_id)
        current_data = None
        current_document = None
        if path.exists():
            self._no_symlink(path)
            current_data = self._read(path)
            if expected_token is None or expected_token != _token(current_data):
                raise ScenarioConflictError(f"Stale save conflict for scenario {document.scenario_id}")
            current_document = deserialize_scenario_document(current_data)
            if current_document.scenario_id != document.scenario_id:
                raise ScenarioConflictError("Managed identity does not match UUID path")
        elif expected_token is not None:
            raise ScenarioConflictError(f"Expected existing scenario: {document.scenario_id}")
        if current_document is not None and _same_content(document, current_document):
            return ScenarioSaveResult(current_document, _token(current_data))
        saved = replace(document,
                        created_at=current_document.created_at if current_document else document.created_at,
                        modified_at=timestamp)
        if self._canonical_validator:
            self._canonical_validator(saved)
        data = serialize_scenario_document_bytes(saved)
        self._atomic_write(path, data)
        return ScenarioSaveResult(saved, _token(data))

    def delete_scenario(self, scenario_id: UUID | str, *, expected_token: str | None = None) -> None:
        identifier = _uuid(scenario_id)
        path = self._path(identifier)
        if not path.exists():
            raise ScenarioNotFoundError(f"Scenario not found: {identifier}")
        self._no_symlink(path)
        if expected_token is not None and _token(self._read(path)) != expected_token:
            raise ScenarioConflictError(f"Stale delete conflict for scenario {identifier}")
        try:
            path.unlink()
        except OSError as exc:
            raise ScenarioStorageError(f"Unable to delete scenario {identifier}") from exc

    def import_scenario(self, source: str | Path, *, now: datetime,
                        scenario_id_factory: Callable[[], UUID] = uuid4,
                        name: str | None = None) -> ScenarioSaveResult:
        source_path = Path(source)
        if source_path.is_symlink():
            raise ScenarioStorageError("Refusing to import from a symlink")
        document = deserialize_scenario_document(self._read(source_path))
        if self._canonical_validator:
            self._canonical_validator(document)
        copied = duplicate_scenario_document(document, now=now, name=name, scenario_id_factory=scenario_id_factory)
        if self._path(copied.scenario_id).exists():
            raise ScenarioConflictError(f"Generated import UUID already exists: {copied.scenario_id}")
        return self.save_scenario(copied, expected_token=None, now=now)

    def export_scenario(self, scenario_id: UUID | str, destination: str | Path, *, overwrite: bool = False) -> ScenarioDocument:
        loaded = self.get_scenario(scenario_id)
        destination = Path(destination)
        if destination.exists() and not overwrite:
            raise ScenarioConflictError(f"Export destination already exists: {destination}")
        if destination.exists() and destination.is_symlink():
            raise ScenarioStorageError("Refusing to overwrite a symlink export destination")
        self._atomic_write(destination, serialize_scenario_document_bytes(loaded.document))
        return loaded.document

    def _ensure_dir(self) -> None:
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            if self._root.is_symlink():
                raise ScenarioStorageError("Repository root cannot be a symlink")
            self._scenario_dir.mkdir(parents=True, exist_ok=True)
            if self._scenario_dir.is_symlink():
                raise ScenarioStorageError("Scenario directory cannot be a symlink")
        except ScenarioPersistenceError:
            raise
        except OSError as exc:
            raise ScenarioStorageError("Unable to initialize scenario repository") from exc

    def _path(self, identifier: UUID) -> Path:
        self._ensure_dir()
        path = self._scenario_dir / f"{identifier}.json"
        if path.parent.resolve() != self._scenario_dir.resolve():
            raise ScenarioStorageError("Managed path escaped repository root")
        return path

    @staticmethod
    def _no_symlink(path: Path) -> None:
        if path.is_symlink():
            raise ScenarioStorageError(f"Refusing to access symlink: {path.name}")

    @staticmethod
    def _read(path: Path) -> bytes:
        try:
            if path.stat().st_size > MAX_SCENARIO_FILE_SIZE:
                raise ScenarioDocumentValidationError("", f"document exceeds {MAX_SCENARIO_FILE_SIZE} bytes")
            return path.read_bytes()
        except ScenarioPersistenceError:
            raise
        except OSError as exc:
            raise ScenarioStorageError(f"Unable to read scenario file: {path}") from exc

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        temp_name = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as temp:
                temp_name = temp.name
                temp.write(data)
                temp.flush()
                os.fsync(temp.fileno())
            os.replace(temp_name, path)
            temp_name = None
        except OSError as exc:
            raise ScenarioStorageError(f"Atomic write failed for {path}") from exc
        finally:
            if temp_name:
                try:
                    Path(temp_name).unlink(missing_ok=True)
                except OSError:
                    pass


def _from_v1(raw: dict[str, object]) -> ScenarioDocument:
    _keys(raw, {"schema_version", "scenario_id", "name", "description", "created_at", "modified_at",
                "game_context", "planning_scenario", "starting_resources", "recruitment_actions", "notes"}, "")
    sid_text = _string(raw["scenario_id"], "scenario_id")
    try:
        scenario_id = UUID(sid_text)
    except ValueError as exc:
        raise ScenarioDocumentValidationError("scenario_id", "must contain a valid UUID") from exc
    context = _object(raw["game_context"], "game_context")
    _keys(context, {"faction", "target", "starting_date"}, "game_context")
    faction = _nonblank(context["faction"], "game_context.faction")
    target = _object(context["target"], "game_context.target")
    _keys(target, {"sid", "level"}, "game_context.target")
    target_sid = _nonblank(target["sid"], "game_context.target.sid")
    target_level = _integer(target["level"], "game_context.target.level", 1)
    starting_date = _game_date(context["starting_date"], "game_context.starting_date")
    scenario = _object(raw["planning_scenario"], "planning_scenario")
    _keys(scenario, {"starting_building_overrides"}, "planning_scenario")
    overrides = []
    for i, value in enumerate(_array(scenario["starting_building_overrides"], "planning_scenario.starting_building_overrides")):
        path = f"planning_scenario.starting_building_overrides[{i}]"
        item = _object(value, path)
        _keys(item, {"sid", "level", "available_at_start"}, path)
        available = item["available_at_start"]
        if type(available) is not bool:
            raise ScenarioDocumentValidationError(f"{path}.available_at_start", "must be a boolean")
        try:
            overrides.append(StartingBuildingOverride(BuildingKey(faction, _nonblank(item["sid"], f"{path}.sid"),
                                                                  _integer(item["level"], f"{path}.level", 1)), available))
        except (TypeError, ValueError) as exc:
            raise ScenarioDocumentValidationError(path, str(exc)) from exc
    resources = _object(raw["starting_resources"], "starting_resources")
    _keys(resources, set(RESOURCE_NAMES), "starting_resources")
    resource_cost = ResourceCost(**{name: _integer(resources[name], f"starting_resources.{name}", 0) for name in RESOURCE_NAMES})
    actions = []
    for i, value in enumerate(_array(raw["recruitment_actions"], "recruitment_actions")):
        path = f"recruitment_actions[{i}]"
        item = _object(value, path)
        _keys(item, {"date", "dwelling", "base_quantity", "upgraded_quantity"}, path)
        dwelling = _object(item["dwelling"], f"{path}.dwelling")
        _keys(dwelling, {"sid", "level"}, f"{path}.dwelling")
        try:
            actions.append(RecruitmentAction(
                _game_date(item["date"], f"{path}.date"),
                BuildingKey(faction, _nonblank(dwelling["sid"], f"{path}.dwelling.sid"),
                            _integer(dwelling["level"], f"{path}.dwelling.level", 1)),
                _integer(item["base_quantity"], f"{path}.base_quantity", 0),
                _integer(item["upgraded_quantity"], f"{path}.upgraded_quantity", 0)))
        except (TypeError, ValueError) as exc:
            raise ScenarioDocumentValidationError(path, str(exc)) from exc
    try:
        planning = PlanningScenario(tuple(overrides))
    except (TypeError, ValueError) as exc:
        raise ScenarioDocumentValidationError("planning_scenario.starting_building_overrides", str(exc)) from exc
    return ScenarioDocument(1, scenario_id, _string(raw["name"], "name"),
                            _string(raw["description"], "description"), _timestamp(raw["created_at"], "created_at"),
                            _timestamp(raw["modified_at"], "modified_at"), faction,
                            BuildingKey(faction, target_sid, target_level), starting_date, planning, resource_cost,
                            tuple(actions), _string(raw["notes"], "notes"))


def _to_object(d: ScenarioDocument) -> dict[str, object]:
    return {
        "schema_version": d.schema_version,
        "scenario_id": str(d.scenario_id),
        "name": d.name,
        "description": d.description,
        "created_at": _format_timestamp(d.created_at),
        "modified_at": _format_timestamp(d.modified_at),
        "game_context": {"faction": d.faction, "target": {"sid": d.target.sid, "level": d.target.level},
                         "starting_date": _date_object(d.starting_date)},
        "planning_scenario": {"starting_building_overrides": [
            {"sid": o.building.sid, "level": o.building.level, "available_at_start": o.available_at_start}
            for o in sorted(d.planning_scenario.starting_building_overrides,
                            key=lambda o: (o.building.sid, o.building.level, o.available_at_start))]},
        "starting_resources": {name: getattr(d.starting_resources, name) for name in RESOURCE_NAMES},
        "recruitment_actions": [{"date": _date_object(a.date),
                                 "dwelling": {"sid": a.dwelling.sid, "level": a.dwelling.level},
                                 "base_quantity": a.base_quantity, "upgraded_quantity": a.upgraded_quantity}
                                for a in d.recruitment_actions],
        "notes": d.notes,
    }


def _same_content(a: ScenarioDocument, b: ScenarioDocument) -> bool:
    return (a.schema_version, a.scenario_id, a.name, a.description, a.faction, a.target, a.starting_date,
            a.planning_scenario, a.starting_resources, a.recruitment_actions, a.notes) == \
           (b.schema_version, b.scenario_id, b.name, b.description, b.faction, b.target, b.starting_date,
            b.planning_scenario, b.starting_resources, b.recruitment_actions, b.notes)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ScenarioDocumentValidationError(key, "duplicate JSON key")
        result[key] = value
    return result


def _depth(value, depth=1):
    if depth > MAX_JSON_NESTING_DEPTH:
        raise ScenarioDocumentValidationError("", f"JSON nesting exceeds {MAX_JSON_NESTING_DEPTH}")
    if isinstance(value, dict):
        for child in value.values():
            _depth(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _depth(child, depth + 1)


def _keys(value, expected, path):
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        field = f"{path}.{missing[0]}" if path else missing[0]
        raise ScenarioDocumentValidationError(field, "required field is missing")
    if unknown:
        field = f"{path}.{unknown[0]}" if path else unknown[0]
        raise ScenarioDocumentValidationError(field, "unknown field")


def _object(value, path):
    if not isinstance(value, dict):
        raise ScenarioDocumentValidationError(path, "must be an object")
    return value


def _array(value, path):
    if not isinstance(value, list):
        raise ScenarioDocumentValidationError(path, "must be an array")
    return value


def _string(value, path):
    if not isinstance(value, str):
        raise ScenarioDocumentValidationError(path, "must be a string")
    return value


def _nonblank(value, path):
    value = _string(value, path)
    if not value.strip():
        raise ScenarioDocumentValidationError(path, "cannot be blank")
    return value


def _integer(value, path, minimum=None):
    if type(value) is not int:
        raise ScenarioDocumentValidationError(path, "must be an integer")
    if minimum is not None and value < minimum:
        raise ScenarioDocumentValidationError(path, f"must be at least {minimum}")
    return value


def _game_date(value, path):
    item = _object(value, path)
    _keys(item, {"month", "week", "day"}, path)
    try:
        return GameDate(_integer(item["month"], f"{path}.month", 1),
                        _integer(item["week"], f"{path}.week"), _integer(item["day"], f"{path}.day"))
    except (TypeError, ValueError) as exc:
        raise ScenarioDocumentValidationError(path, str(exc)) from exc


def _timestamp(value, path):
    text = _string(value, path)
    if not _TIMESTAMP_RE.fullmatch(text):
        raise ScenarioDocumentValidationError(path, "must use UTC format YYYY-MM-DDTHH:MM:SSZ")
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ScenarioDocumentValidationError(path, "contains an invalid UTC timestamp") from exc


def _format_timestamp(value):
    return _require_utc(value, "timestamp").strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_utc(value, path):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ScenarioDocumentValidationError(path, "must be a timezone-aware UTC datetime")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ScenarioDocumentValidationError(path, "must be UTC")
    if value.microsecond:
        raise ScenarioDocumentValidationError(path, "fractional seconds are not supported")
    return value.astimezone(timezone.utc)


def _validate_text(value, path, maximum):
    if not isinstance(value, str):
        raise ScenarioDocumentValidationError(path, "must be a string")
    if len(value) > maximum:
        raise ScenarioDocumentValidationError(path, f"must contain at most {maximum} Unicode code points")


def _date_object(date):
    return {"month": date.month, "week": date.week, "day": date.day}


def _action_key(action):
    return (action.date.day_index, action.dwelling.sid, action.dwelling.level,
            action.base_quantity, action.upgraded_quantity)


def _token(data):
    return sha256(data).hexdigest()


def _uuid(value):
    if isinstance(value, UUID):
        return value
    if not isinstance(value, str):
        raise ScenarioDocumentValidationError("scenario_id", "must be a UUID or UUID string")
    try:
        return UUID(value)
    except ValueError as exc:
        raise ScenarioDocumentValidationError("scenario_id", "must contain a valid UUID") from exc


def _canonical_filename(filename):
    if not filename.endswith(".json"):
        return False
    try:
        value = UUID(filename[:-5])
    except ValueError:
        return False
    return str(value) == filename[:-5]


def _require_document(document):
    if not isinstance(document, ScenarioDocument):
        raise TypeError("document must be a ScenarioDocument")
