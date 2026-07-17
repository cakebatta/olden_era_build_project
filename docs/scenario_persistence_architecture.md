# Scenario Persistence Architecture

## Purpose

This document defines the canonical Version 1 persistence architecture for planning scenarios. It specifies the external JSON contract, immutable in-memory boundaries, deterministic serialization, repository behavior, validation, compatibility, errors, storage safety, conflicts, and required examples.

No production persistence code is introduced by DE-005.

## Architectural position

The existing application flow remains:

```text
Persisted or newly authored scenario intent
        ↓
Authoritative Query Layer
        ↓
Deterministic analysis
        ↓
Presentation
```

Persistence supplies user intent to this flow. It does not become an analysis layer.

The persistence stack is:

```text
ScenarioDocument
        ↓
ScenarioSerializer
        ↓
ScenarioRepository
        ↓
Storage implementation
```

Application code depends on repository and serializer abstractions, not direct filesystem access.

## PlanningScenario versus ScenarioDocument

### PlanningScenario

`PlanningScenario` remains the immutable domain description of starting-building overrides.

It owns only:

- `StartingBuildingOverride` values;
- each override's `BuildingKey`;
- each override's `available_at_start` flag;
- domain validation such as duplicate-override rejection.

It must not own UUIDs, names, timestamps, notes, target selection, starting resources, recruitment actions, paths, repository state, or serialization concerns.

### ScenarioDocument

`ScenarioDocument` is the immutable in-memory representation of a persisted user workspace.

Conceptually:

```text
ScenarioDocument
├── schema and identity metadata
├── game context
│   ├── faction
│   ├── target BuildingKey
│   └── starting GameDate
├── PlanningScenario
├── starting ResourceCost
├── recruitment actions
├── description
└── notes
```

`ScenarioDocument` composes existing domain values. It does not replace them.

## Version 1 contents

Version 1 contains:

- schema version;
- UUID;
- name;
- description;
- creation and modification timestamps;
- faction;
- selected target SID and level;
- starting month/week/day;
- starting-building overrides;
- every canonical resource value;
- recruitment actions;
- notes.

All fields are required. Empty-content fields use empty strings or arrays, never `null`.

## Derived-data exclusion

The persisted schema must never contain:

- dependency graphs;
- legal build orders;
- `BuildPlan` or construction steps;
- cumulative-cost results;
- `IncomeTimeline` or income entries;
- `RecruitmentStock` or stock snapshots;
- `ResourceLedger` or daily balances;
- feasibility or deficit results;
- comparisons or Decision Summaries;
- localized display text;
- formatted desktop rows;
- UI identifiers, layout state, or transient errors;
- repository paths or conflict tokens.

These are regenerated from current canonical data and current backend rules.

## Normative JSON structure

```json
{
  "schema_version": 1,
  "scenario_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Early Economy Rush",
  "description": "",
  "created_at": "2026-07-16T22:30:00Z",
  "modified_at": "2026-07-16T22:30:00Z",
  "game_context": {
    "faction": "human",
    "target": {
      "sid": "Build_Main",
      "level": 2
    },
    "starting_date": {
      "month": 1,
      "week": 1,
      "day": 1
    }
  },
  "planning_scenario": {
    "starting_building_overrides": []
  },
  "starting_resources": {
    "gold": 0,
    "wood": 0,
    "ore": 0,
    "gemstones": 0,
    "crystals": 0,
    "mercury": 0,
    "dust": 0,
    "graal": 0
  },
  "recruitment_actions": [],
  "notes": ""
}
```

The field names reflect current domain contracts: `GameDate` uses month/week/day, and `ResourceCost` uses `gold`, `wood`, `ore`, `gemstones`, `crystals`, `mercury`, `dust`, and `graal`.

## Field contract

### Top level

| Field | Type | Rules |
|---|---|---|
| `schema_version` | integer | Required; exactly `1`; boolean rejected. |
| `scenario_id` | string | Required canonical UUID. |
| `name` | string | Trimmed, nonblank, at most 120 Unicode code points. |
| `description` | string | Required; empty allowed; at most 500 code points. |
| `created_at` | string | Required normative UTC timestamp. |
| `modified_at` | string | Required normative UTC timestamp; not earlier than `created_at`. |
| `game_context` | object | Required. |
| `planning_scenario` | object | Required. |
| `starting_resources` | object | Required. |
| `recruitment_actions` | array | Required. |
| `notes` | string | Required; empty allowed; at most 20,000 code points. |

### game_context

`game_context` contains exactly:

- `faction`: nonblank string;
- `target`: object with nonblank `sid` and integer `level >= 1`;
- `starting_date`: object with integer `month >= 1`, `week` 1–4, and `day` 1–7.

The target faction is inherited from `game_context.faction` and reconstructed as `BuildingKey(faction, sid, level)`.

### planning_scenario

```json
{
  "starting_building_overrides": [
    {
      "sid": "Build_Main",
      "level": 1,
      "available_at_start": true
    }
  ]
}
```

Each entry requires:

- `sid`: nonblank string;
- `level`: integer at least 1;
- `available_at_start`: exact JSON boolean.

Faction is inherited from `game_context.faction`.

Duplicate `(sid, level)` entries are invalid.

Canonical serialization orders overrides by `sid`, then `level`. A final false-before-true tie-breaker may be used internally, but a valid document cannot contain both because duplicate building overrides are invalid.

### starting_resources

This object contains exactly these required integer keys in this order:

1. `gold`
2. `wood`
3. `ore`
4. `gemstones`
5. `crystals`
6. `mercury`
7. `dust`
8. `graal`

Values are nonnegative JSON integers. Booleans, strings, floats, NaN, and infinity are invalid.

### recruitment_actions

Each action is:

```json
{
  "date": {
    "month": 1,
    "week": 2,
    "day": 1
  },
  "dwelling": {
    "sid": "Build_Tier_1",
    "level": 1
  },
  "base_quantity": 4,
  "upgraded_quantity": 0
}
```

Rules:

- `date` must construct a valid `GameDate`;
- dwelling SID is nonblank and level is at least 1;
- dwelling faction is inherited from `game_context.faction`;
- quantities are nonnegative integers;
- total quantity is at least 1, as required by `RecruitmentAction`.

Recruitment actions are chronological user intent. Canonical serialization sorts by:

1. date day index, equivalent to month/week/day;
2. dwelling SID;
3. dwelling level;
4. base quantity;
5. upgraded quantity.

Version 1 has no recruitment-action UUID. Exact duplicate actions are invalid because they are indistinguishable and add no distinct intent.

## Required fields, defaults, nulls, and unknown fields

All Version 1 fields are required when reading JSON.

Creation defaults are:

- `description = ""`;
- starting date 1/1/1;
- empty starting-building overrides;
- every resource zero;
- empty recruitment actions;
- `notes = ""`.

Defaults are creation behavior only. A reader must not silently fill missing fields.

Explicit `null` is invalid everywhere.

Unknown fields are rejected at every schema-defined object boundary. Strict rejection prevents misspellings and unsupported semantics from being lost on a later save.

## UUID semantics

Use UUID text accepted by the platform UUID parser and emit canonical lowercase hyphenated form.

- Save, Rename, Load, Open, and Export preserve UUID.
- Duplicate, Save As, and import-as-copy generate a new UUID.
- Repository filenames are `<canonical-uuid>.json`.
- Display names never determine paths.

## Timestamp semantics

External format:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Rules:

- UTC only;
- no fractional seconds in Version 1;
- `created_at` is generated once per logical scenario;
- `created_at` never changes during ordinary edits, Save, Rename, Load, or Export;
- `modified_at` records the latest successful content save;
- Load, Export, and analysis do not change timestamps;
- Rename updates `modified_at` when successfully saved;
- Duplicate, Save As, and import-as-copy generate new UUIDs and new equal creation/modification timestamps.

Clock acquisition must be injectable or controllable in tests.

## Deterministic serialization

Canonical JSON is:

- UTF-8 without BOM;
- human-readable two-space indentation;
- one space after `:`;
- no tabs or trailing whitespace;
- one final newline;
- Unicode emitted directly rather than unnecessarily escaped;
- no comments;
- no NaN or infinity;
- no Python class names or object representations;
- no tuples or sets in the external form.

Keys are emitted in the normative order shown above, including nested objects. Resource keys use canonical resource order. Starting-building overrides and recruitment actions use the defined canonical sorting keys.

Description and notes are preserved exactly after JSON decoding. The serializer does not normalize line endings inside strings. Name trimming is product validation, not general text normalization.

Two semantically equal `ScenarioDocument` values serialize to byte-identical JSON unless a deliberate metadata update changes `modified_at`.

### Serialize exactly

A pure serializer:

- validates the in-memory document;
- emits exactly its metadata;
- does not read a clock;
- does not mutate timestamps;
- does not perform file I/O.

### Save with metadata update

A save operation:

1. compares current persisted user content with the clean baseline;
2. if changed, constructs a new immutable document with a new `modified_at`;
3. serializes it;
4. performs an atomic write;
5. establishes the new clean baseline only after success.

A no-op Save may preserve `modified_at`.

## Versioning and compatibility

Version 1 uses:

- `schema_version` for the JSON contract;
- UUID for logical scenario identity;
- `modified_at` plus an opaque repository conflict token for concurrency.

No user-visible integer revision is added before revision history exists.

Reader behavior:

- missing version: invalid;
- boolean or non-integer version: invalid;
- version 1: accepted after Version 1 validation;
- older version: accepted only when an explicit migration exists;
- newer or unknown version: `UnsupportedScenarioVersionError`;
- unknown versions are never reinterpreted as Version 1.

Future read pipeline:

```text
raw JSON
    ↓
safe parsing and version detection
    ↓
schema-specific structural validation
    ↓
explicit one-version migration steps
    ↓
domain construction
    ↓
current ScenarioDocument
```

Migrations must be explicit, deterministic, testable, chained one version at a time, and non-destructive to the source file. DE-005 implements none.

## Validation boundaries

### Document validation

Checks:

- top-level object;
- file-size and nesting limits;
- duplicate JSON keys where detectable;
- required and unknown fields;
- exact primitive types;
- UUID and timestamp syntax;
- supported schema;
- string limits;
- nonnegative resource values;
- list shapes and duplicate entries.

Errors include field-path context.

### Domain validation

Constructs and delegates to existing contracts:

- `BuildingKey`;
- `GameDate`;
- `ResourceCost`;
- `StartingBuildingOverride`;
- `PlanningScenario`;
- `RecruitmentAction`;
- `ScenarioDocument`.

Persistence does not duplicate rules already owned by domain constructors. Errors may propagate when clear or be wrapped with field-path context while preserving the original cause.

### Canonical-data validation

Requires loaded game data and checks:

- faction exists;
- target SID and level exist for the faction;
- each override building exists and belongs to the faction;
- overrides are meaningful against canonical starting state;
- each recruitment dwelling exists and is dwelling-linked;
- all references belong to the document faction.

Conceptual separation:

```text
deserialize_document(...)
validate_document_against_game_data(...)
```

Deserialization does not require a database. Analysis cannot proceed until canonical-data validation succeeds.

## Component responsibilities

### ScenarioDocument

An immutable aggregate of persisted user intent and metadata. It has no filesystem or analysis methods.

### ScenarioSerializer

Responsible for:

- safe JSON decoding;
- duplicate-key detection where supported;
- schema detection and structural validation;
- domain construction;
- future migration dispatch;
- deterministic encoding;
- field-path errors.

It must not read or write files, update timestamps, generate UUIDs, manage indexes, query game data, analyze scenarios, or call desktop code.

### ScenarioRepository

Responsible for:

- list;
- retrieve by UUID;
- save;
- delete;
- collision detection;
- stale-save detection;
- repository-owned locations;
- import;
- export;
- valid summaries plus invalid-entry diagnostics.

It must not calculate analysis, contain GUI behavior, alter domain semantics, derive paths from names, or inspect canonical game rules.

### Storage implementation

Version 1 stores one JSON document per scenario in a local application-data directory:

```text
<application-data>/
└── scenarios/
    ├── <uuid>.json
    └── <uuid>.json
```

`<application-data>` is the platform-neutral per-user application-data location chosen by the bootstrap/storage layer. It is not the Git repository, current working directory, or an OS-specific path embedded in domain logic.

## Repository observable contract

Exact Python signatures remain a BE-025 implementation decision, but observable behavior is fixed.

### list_scenarios

Returns valid scenario summaries and separate diagnostics for invalid or inaccessible entries. One malformed file does not block all valid scenarios. Summaries come from validated document contents, not filenames.

Default summary ordering is name casefold, then original name, then UUID.

### get_scenario

Validates UUID input, resolves only its UUID-owned path, reads with limits, deserializes, and returns the document plus an opaque conflict token. Missing UUID raises not-found. No analysis occurs.

### save_scenario

Saves by document UUID. It creates a new file if absent and updates an existing file only when the caller's expected conflict token matches. A stale mismatch raises conflict. It writes atomically and returns the saved document plus a new token.

### delete_scenario

Deletes by UUID, optionally requiring the expected token. It never accepts arbitrary paths. Missing UUID raises not-found.

### import_scenario

Reads an explicitly chosen external file, validates before repository mutation, and never silently overwrites a matching UUID. Version 1 supports import-as-copy. A failed import leaves the repository unchanged.

### export_scenario

Retrieves the current saved document, serializes without metadata mutation, and writes to an explicitly chosen destination. Existing destinations require deliberate overwrite authorization.

## Atomic-save requirement

Managed saves must:

1. serialize fully before touching the destination;
2. create a temporary file in the destination directory;
3. write all bytes;
4. flush and close it;
5. flush durable file content where supported;
6. atomically replace the UUID-owned destination;
7. remove temporary files after failure.

A partial canonical file must never be reported as a successful save.

## Concurrency and conflicts

Version 1 requires stale-save conflict detection.

When loading, the repository returns an opaque token derived from exact stored bytes or equivalent stable content state. SHA-256 of the stored bytes is recommended.

On Save or Delete:

- caller supplies its last-known token;
- repository checks current content;
- mismatch raises `ScenarioConflictError`;
- no automatic merge occurs;
- newer content is not silently overwritten.

`modified_at` is not sufficient alone because it has one-second precision and external edits may preserve metadata.

Conflict tokens are repository state and are never serialized into the portable document.

## Malformed repository entries

Repository listing uses partial-success behavior:

- return all valid summaries;
- separately return invalid-entry diagnostics;
- do not delete, rename, or rewrite malformed entries;
- do not expose stack traces to product UI.

Diagnostics identify the repository-owned filename, safe error category, and concise message.

## Error model

Conceptual hierarchy:

```text
ScenarioPersistenceError
├── ScenarioSerializationError
├── ScenarioDocumentValidationError
├── UnsupportedScenarioVersionError
├── ScenarioNotFoundError
├── ScenarioConflictError
└── ScenarioStorageError
```

Responsibilities:

- serialization: JSON encoding/decoding failures;
- document validation: schema and persisted-domain field failures;
- unsupported version: unknown or newer schema;
- not found: missing managed UUID;
- conflict: UUID collision or stale save;
- storage: filesystem and I/O failures.

Field errors identify paths such as:

- `planning_scenario.starting_building_overrides[2].level`;
- `recruitment_actions[1].date.week`;
- `starting_resources.gold`.

Product-facing messages never show raw stack traces.

## Security and robustness

Version 1 requires:

- top-level JSON object;
- maximum file size of 1 MiB before parsing;
- maximum nesting depth of 32;
- duplicate JSON key rejection where detectable;
- strict unknown-field rejection;
- UUID-owned repository filenames;
- no path derivation from display names;
- deletion by UUID, not path;
- explicit export destinations and overwrite authorization;
- imported filenames treated as untrusted;
- no following symlinks inside the managed scenario directory for read, replace, or delete;
- resolved managed paths verified to remain within the configured directory;
- no executable or arbitrary-object deserialization.

Hostile multi-user security is outside scope, but obvious unsafe file handling is prohibited.

## Portability

Portable scenario documents contain no absolute paths, app-data paths, repository paths, cached objects, UI identifiers, Python modules or classes, OS metadata, or conflict tokens.

Import validates before repository mutation. Export preserves the saved UUID. “Export as copy” is outside Version 1.

## Desktop boundary

The desktop may present summaries, choose an active scenario, collect edits, track dirty state, request repository operations, prompt about unsaved work, present safe errors, and submit loaded intent to the Query Layer.

It must not read or write JSON, generate UUID paths, choose app-data directories, migrate schemas, compute conflict tokens, inspect filesystem entries, or independently validate canonical references.

## Query Layer boundary

Persistence may supply faction, target, starting date, `PlanningScenario`, starting resources, and recruitment actions. Notes and metadata are not analysis inputs.

Loading does not itself call Query Layer methods. The Query Layer retains orchestration authority for plans, income, stock, ledgers, comparisons, and summaries.

## Validation examples

### Minimal valid scenario

The normative example at the start of this document with empty overrides/actions and zero resources:

- structural deserialization: succeeds;
- domain validation: succeeds;
- canonical-data validation: succeeds only when the faction and target exist;
- repository save: succeeds if UUID does not collide.

### Fully populated scenario

```json
{
  "schema_version": 1,
  "scenario_id": "8992ba4a-326d-4e94-9820-f02a3407db71",
  "name": "Early Economy Rush",
  "description": "Accelerated main-building path with early recruiting.",
  "created_at": "2026-07-16T22:30:00Z",
  "modified_at": "2026-07-16T23:15:12Z",
  "game_context": {
    "faction": "human",
    "target": {"sid": "Build_Main", "level": 3},
    "starting_date": {"month": 1, "week": 1, "day": 1}
  },
  "planning_scenario": {
    "starting_building_overrides": [
      {"sid": "Build_Main", "level": 1, "available_at_start": true},
      {"sid": "Build_Tier_1", "level": 1, "available_at_start": false}
    ]
  },
  "starting_resources": {
    "gold": 10000,
    "wood": 10,
    "ore": 10,
    "gemstones": 5,
    "crystals": 5,
    "mercury": 5,
    "dust": 50,
    "graal": 0
  },
  "recruitment_actions": [
    {
      "date": {"month": 1, "week": 1, "day": 4},
      "dwelling": {"sid": "Build_Tier_1", "level": 1},
      "base_quantity": 6,
      "upgraded_quantity": 0
    }
  ],
  "notes": "Keep the economy branch available for comparison."
}
```

- structural deserialization: succeeds;
- domain validation: succeeds;
- canonical-data validation: depends on all human references;
- normal update: requires matching conflict token.

### Imported duplicate UUID

A valid external document uses an existing managed UUID:

- structural deserialization: succeeds;
- domain validation: succeeds;
- canonical-data validation: evaluated normally;
- registration under same UUID: conflict;
- import-as-copy: new UUID and timestamps, source content preserved;
- existing managed file: unchanged.

### Unsupported future schema

```json
{"schema_version": 99}
```

- version detection: succeeds;
- Version 1 deserialization: stops;
- domain and canonical validation: do not run;
- error: `UnsupportedScenarioVersionError`;
- repository unchanged.

### Malformed recruitment action

An action has `base_quantity: -1`:

- structural integer-shape validation: succeeds;
- domain construction: fails through `RecruitmentAction`;
- error path identifies the action and quantity;
- canonical validation does not run;
- import leaves repository unchanged.

### Unknown building reference

A structurally valid target uses `Build_Does_Not_Exist`:

- structural deserialization: succeeds;
- domain validation: succeeds because the key is syntactically valid;
- canonical-data validation: fails;
- analysis is prohibited;
- managed import fails before repository mutation;
- portable inspection may still show the document and diagnostic.

## Decision log

1. **PlanningScenario versus ScenarioDocument:** `PlanningScenario` remains starting-building domain state; `ScenarioDocument` is the persisted workspace aggregate.
2. **Version 1 fields:** identity metadata, description, faction, target, starting date, overrides, all canonical resources, recruitment actions, and notes.
3. **Stable UUID:** preserved by edit, rename, Save, Load, and Export; regenerated by Duplicate, Save As, and import-as-copy.
4. **Duplicate names:** allowed because UUID is authoritative.
5. **Repository filenames:** canonical UUID plus `.json`; names never determine paths.
6. **Import collision:** never overwrite silently; Version 1 exposes import-as-copy; replacement deferred.
7. **Timestamps:** UTC `YYYY-MM-DDTHH:MM:SSZ`; no fractions; `created_at` stable; successful content save updates `modified_at`.
8. **Unknown fields:** rejected at every Version 1 object boundary.
9. **Validation separation:** deserialization performs structural/domain validation; game-data validation is separate.
10. **Serialization:** UTF-8, two-space deterministic JSON, normative key order, canonical list order, final newline, pure serializer does not mutate metadata.
11. **Atomic saves:** required.
12. **Conflict detection:** required using an opaque last-known content token; no merge.
13. **Malformed entries:** valid summaries plus separate diagnostics; one bad file does not block listing.
14. **Derived data:** entirely excluded and regenerated.
15. **Dirty state:** based on persisted user intent versus clean semantic baseline; analysis and presentation changes do not count.

## Scope boundaries

This architecture does not design cloud sync, Steam Cloud, accounts, collaboration, revision history, automatic merging, encryption, compressed formats, result caching, autosave, tags, folders, or UI layout.
