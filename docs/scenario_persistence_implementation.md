# Scenario Persistence Implementation

## Purpose

BE-025 implements the Version 1 persistence foundation defined by DE-005. Persistence stores immutable user-authored scenario intent and never stores or generates analysis results.

## Module

The implementation is located in:

```text
olden_db/olden_db/scenario_persistence.py
```

It contains four distinct responsibilities:

```text
ScenarioDocument
        ↓
serialization and deserialization
        ↓
LocalScenarioRepository
        ↓
<configured root>/scenarios/<uuid>.json
```

The module reuses `BuildingKey`, `GameDate`, `ResourceCost`, `PlanningScenario`, `StartingBuildingOverride`, and `RecruitmentAction`. It does not call the Query Layer.

## Immutable document contract

`ScenarioDocument` is frozen and contains only Version 1 persisted intent:

- schema version and UUID;
- name, description, notes, and UTC timestamps;
- faction and target `BuildingKey`;
- starting `GameDate`;
- `PlanningScenario`;
- starting `ResourceCost`;
- an immutable, canonical tuple of `RecruitmentAction` values.

Creation and duplication are explicit through `create_scenario_document()` and `duplicate_scenario_document()`. Pure deserialization preserves UUID and timestamps.

## Serialization API

```python
serialize_scenario_document(document) -> str
serialize_scenario_document_bytes(document) -> bytes
deserialize_scenario_document(data) -> ScenarioDocument
```

Canonical output is UTF-8, strict JSON, two-space indented, deterministically ordered, and terminated by one newline. Serialization performs no file access, clock access, UUID generation, or metadata update.

The reader rejects duplicate keys, non-object top levels, missing or malformed schema versions, unsupported versions, unknown fields, explicit nulls, invalid primitive types, invalid timestamps, excessive size, and excessive nesting.

## Validation sequence

Deserialization performs structural validation and constructs existing domain contracts. Canonical game-data validation remains separate:

```python
validate_document_against_game_data(document, loaded_game_data)
```

This operation validates faction, target, meaningful starting-building overrides, and recruitment dwelling references. A repository can receive a canonical validation callback when admission-time validation is required.

## Repository construction

```python
repository = LocalScenarioRepository(
    root_directory,
    canonical_validator=lambda document: validate_document_against_game_data(
        document,
        loaded_game_data,
    ),
)
```

The root is supplied by the caller. No operating-system application-data path is hard-coded.

Observable operations are:

```python
list_scenarios()
get_scenario(scenario_id)
save_scenario(document, expected_token=..., now=...)
delete_scenario(scenario_id, expected_token=...)
import_scenario(source, now=..., scenario_id_factory=...)
export_scenario(scenario_id, destination, overwrite=False)
```

Loads and saves return an opaque SHA-256 conflict token derived from exact stored bytes. Updating an existing scenario requires the last observed token. A mismatch raises `ScenarioConflictError`.

Managed saves write a complete temporary file in the destination directory, flush and fsync it, and use `os.replace()` for atomic replacement. Repository filenames are canonical UUIDs and never scenario names.

Repository listing returns valid summaries and separate malformed-entry diagnostics. Invalid entries are not deleted or rewritten.

## Import and export

Version 1 import is import-as-copy. The external document is size-checked, decoded, structurally/domain validated, optionally canonical-data validated, duplicated with a new UUID and timestamps, and only then atomically admitted to the repository.

Export retrieves the saved managed document and writes its exact portable Version 1 representation. It preserves UUID and timestamps, does not update `modified_at`, and does not alter repository membership. Existing destinations require `overwrite=True`.

## Validation

From the outer `olden_db/` directory:

```bash
python -m scripts.test_scenario_serialization
python -m scripts.test_scenario_validation
python -m scripts.test_scenario_repository
```

Relevant regressions:

```bash
python -m scripts.test_query_scenarios
python -m scripts.test_query_resource_ledger
python -m scripts.test_query_income_resource_ledger
python -m scripts.test_resource_ledger
python -m scripts.test_desktop_income_timeline
```
