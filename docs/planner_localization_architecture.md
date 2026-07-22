# Planner Localization Architecture

## Status

**Decision:** Approved  
**Work item:** ARCH-021 — Planner Localization Architecture  
**Sprint:** 17 — Presentation Infrastructure  
**Depends on:** Query Layer, canonical data models  
**Authorizes:** BE-014 — Planner Localization Catalog  
**Production behavior changed by this document:** None

## Purpose

This document defines the authoritative architecture for planner-facing localization.

The application must display canonical game names for planner-visible factions, buildings, building upgrades, units, recruitment entries, milestones, and future planner entities without changing canonical identity, weakening existing localization-parser validation, or allowing presentation code to read localization assets.

The approved solution is a dedicated `PlannerLocalizationCatalog`.

The catalog is a planner-scoped read model. It is not a general-purpose replacement for the existing localization parser and it does not redefine localization-file semantics.

## Background

The existing localization parser treats a merged localization collection as one globally unique key namespace.

Its current behavior is intentional:

- parsing one localization file creates a `LocalizationCatalog`;
- merging explicit files or a directory sorts and parses those files deterministically;
- duplicate keys with identical text are permitted;
- duplicate keys with conflicting text raise `DuplicateLocalizationKeyError`;
- no file silently overrides another.

The game localization assets use some localization identifiers independently in different files. Parsing the complete localization directory through the existing merge contract can therefore produce legitimate duplicate-key conflicts.

This is not a parser defect.

The planner must not solve the problem by changing duplicate handling, suppressing conflicts, or applying file-order precedence. Instead, planner-facing localization must select and index only the localization records required by planner-visible canonical entities.

## Decision

Introduce an immutable application-backend component:

```text
PlannerLocalizationCatalog
```

The catalog is constructed from:

1. canonical loaded game data;
2. an explicit planner-localization source policy;
3. narrowly selected localization documents or alternate display-name sources;
4. one requested language.

The catalog exposes deterministic display-name lookup for supported planner entities.

The Query Layer owns the catalog instance and exposes stable lookup operations.

```text
Canonical game assets
    ↓
Existing parsers and canonical models
    ↓
LoadedGameData
    ├─────────────────────────────┐
    │                             │
Planner localization source      │
selection and indexing           │
    ↓                             │
PlannerLocalizationCatalog       │
    └──────────────┬──────────────┘
                   ↓
          PlanningQueryService
                   ↓
             Presenters
                   ↓
          immutable presentation
                   ↓
             passive views
```

Raw localization documents do not cross the Planner Localization Catalog boundary.

## Architectural Principles

### Canonical identity remains authoritative

Localization never becomes identity.

Planner algorithms, persistence, comparisons, scenarios, workspace state, recruitment accounting, and canonical discovery continue to use canonical identifiers such as:

- faction SID;
- building SID;
- `BuildingKey`;
- unit SID;
- canonical upgrade SID;
- canonical planner entity identity.

Localized display names are derived presentation values.

Changing language or localization source must not change planner output, persistence identity, comparison membership, or workspace identity.

### Existing parser semantics remain unchanged

ARCH-021 does not authorize modifications to:

- `LocalizationCatalog`;
- `parse_localization_file(...)`;
- `parse_localization_files(...)`;
- `parse_localization_directory(...)`;
- `DuplicateLocalizationKeyError`;
- duplicate-key validation;
- merge ordering;
- fallback behavior already documented for the existing parser.

The existing parser remains valid for a localization document or an explicit set of documents whose keys are intended to share one namespace.

The Planner Localization Catalog may use existing single-file parsing or other approved low-level reading functions internally, but it must not reinterpret conflicting duplicates as valid members of one merged parser catalog.

### Planner scope is explicit

The catalog indexes only entities that can appear in planner-facing output.

It intentionally excludes unrelated interface localization, including:

- menus;
- profiles;
- launcher text;
- editor text;
- settings;
- unrelated tutorials;
- general application chrome;
- non-planner game interfaces.

### Determinism

For the same:

- canonical game data;
- language;
- planner-localization source policy;
- source contents;

the catalog and every lookup result must be identical.

Filesystem enumeration order, hash-map order, UI traversal order, and lookup timing must not alter results.

### Presentation isolation

Presenters request display names from the Query Layer.

Presenters do not:

- parse localization;
- select files;
- resolve paths;
- cache raw token maps;
- know source precedence;
- implement fallback ordering.

Views receive display-ready immutable strings only.

## Existing Localization Parser Ownership

The existing localization parser retains responsibility for:

- validating localization-document structure;
- reading supported localization JSON documents;
- producing the existing `LocalizationCatalog`;
- detecting conflicting duplicate keys within one parsed namespace;
- deterministic explicit-file and directory merge behavior;
- existing `get(...)`, `resolve(...)`, and `contains(...)` contracts.

The parser does not own:

- planner-entity discovery;
- planner-specific source selection;
- faction, building, unit, or milestone semantics;
- cross-file namespace interpretation;
- Query Layer display-name APIs;
- UI presentation.

No behavioral changes are authorized under ARCH-021.

## Planner Localization Catalog

### Responsibility

`PlannerLocalizationCatalog` is the authoritative planner-facing display-name index for one language and one canonical game-data snapshot.

It owns:

- planner-visible entity indexing;
- deterministic association between canonical planner identities and display names;
- planner-specific source filtering;
- fallback metadata required for deterministic resolution;
- immutable lookup state;
- language identity;
- validation that every indexed entry corresponds to an allowed planner entity.

It does not own:

- canonical game-data identity;
- parser behavior;
- planner algorithms;
- scenario state;
- workspace state;
- persistence;
- UI rendering;
- presentation layout;
- general application localization.

### Conceptual contract

```text
PlannerLocalizationCatalog
    language
    faction_names
    building_names
    unit_names
    upgrade_names
    milestone_names
```

The exact internal maps are implementation details.

Keys must be typed or structurally unambiguous canonical planner identities. One flat global string-key dictionary is not the approved public design because identical raw strings may be meaningful in different entity categories or source domains.

Recommended conceptual key types include:

```text
FactionLocalizationKey
    faction_sid

BuildingLocalizationKey
    BuildingKey

UnitLocalizationKey
    faction_sid
    unit_sid

UpgradeLocalizationKey
    faction_sid
    upgrade_sid

MilestoneLocalizationKey
    milestone_id
```

BE-014 may use existing canonical types directly where they are already sufficient.

New public identity classes must not be introduced merely to wrap strings unless they prevent real ambiguity or improve contract safety.

### Immutable catalog

After successful construction, the catalog is immutable.

Recommended implementation characteristics:

- frozen dataclass or equivalent immutable public object;
- mapping values exposed as immutable mappings or hidden entirely;
- no mutation methods;
- no lazy insertion during lookup;
- no presenter-owned cache;
- no view-owned cache.

Internal temporary mutable dictionaries are allowed during construction and must not escape the builder.

### Catalog completeness

Catalog construction need not fail merely because optional localized text is absent. Missing localization is handled through the approved fallback policy.

Construction must fail for structural or policy errors that would make lookup nondeterministic, including:

- ambiguous source assignment for the same planner entity;
- conflicting planner names at the same approved precedence;
- unsupported language configuration;
- malformed required source data;
- a catalog entry associated with an invalid canonical entity;
- unordered source precedence.

## Supported Entities

The first implementation must support at least:

### Factions

Canonical input:

```text
faction SID
```

Output:

```text
display-ready faction name
```

### Buildings

Canonical input:

```text
BuildingKey
```

A building level remains part of canonical identity even when multiple levels share one display name.

### Building upgrades

The catalog must support planner-visible upgraded building identities.

Where an upgrade is represented by a `BuildingKey`, the building lookup is authoritative.

If future canonical data introduces a distinct upgrade identity, an additive typed lookup may be added without redesigning catalog ownership.

### Units

Canonical input must include enough canonical context to avoid ambiguity. At minimum:

```text
faction SID
unit SID
```

A bare localized token is never unit identity.

### Recruitment entries

Recruitment presentation resolves the unit or upgrade identity contained in the canonical recruitment entry.

The catalog does not own recruitment quantities, dates, availability, or costs.

### Planner-visible milestones

Milestones must have stable canonical application identities defined by the owning planner or analysis feature.

The catalog supplies only their display names.

It does not decide which milestones exist or when they occur.

### Future entities

Additional planner-visible entity categories may add typed indexes and Query Layer methods.

Adding a category should require:

1. a canonical identity owned outside localization;
2. an approved way to discover planner-visible members;
3. a deterministic display-name source;
4. a fallback source;
5. tests.

It must not require changing parser duplicate semantics.

## Planner Entity Discovery

Planner-relevant localization is identified from canonical planner data, not from broad localization-directory scanning.

The catalog builder begins with canonical entities already loaded by backend parsers.

Examples:

- factions come from loaded canonical cities;
- buildings come from `FactionCity.buildings`;
- building display-key candidates come from `BuildingLevel.name_key`;
- unit and upgrade SIDs come from canonical `UnitFamily` data;
- recruitment entities come from canonical unit families and recruitment contracts;
- milestones come from an explicit canonical registry owned by the feature that defines them.

This produces an allowlist of planner entity identities and candidate localization references.

The builder then reads only approved source documents or alternate sources capable of resolving that allowlist.

The builder must not infer planner relevance by:

- scanning every localization file;
- selecting every token with a naming prefix;
- accepting every token encountered in a directory;
- using UI labels as canonical entity discovery;
- using localized text to join canonical records.

## Source Policy

### Explicit source manifest

The recommended implementation uses an explicit, deterministic source manifest or source-provider configuration.

Conceptually:

```text
PlannerLocalizationSourcePolicy
    language
    faction_sources
    building_sources
    unit_sources
    upgrade_sources
    milestone_sources
```

The source policy may resolve repository paths through `paths.py`, but repository layout remains hidden from callers and presenters.

Sources may be:

- an explicit localization file;
- an explicit ordered tuple of files known to share one namespace;
- a canonical game-data display-name field;
- a generated planner-owned localization resource;
- a future language pack implementing the same provider contract.

A complete directory glob is not an approved default planner source.

### Source precedence

For each planner entity and language, source precedence must be explicit.

Sources at the same precedence must not produce conflicting text for the same planner entity.

There is no implicit “last file wins” behavior.

### No handwritten entity dictionary

BE-014 must not solve localization by committing a manually maintained dictionary of faction, building, and unit names.

A small declarative source manifest is allowed when it identifies source documents or provider types rather than duplicating localized game text.

Planner-owned milestone labels may use an explicit planner resource because those identities may not exist in game localization. Such resources remain data, not presenter constants.

## Lookup Contract

### General requirements

Every public lookup operation:

- accepts canonical identity;
- returns one display-ready `str`;
- is deterministic;
- does not mutate the catalog;
- does not expose raw localization keys;
- does not expose the underlying token map;
- applies the same fallback policy;
- validates the canonical identity category;
- is safe for repeated concurrent reads after construction.

Recommended catalog methods:

```text
get_faction_display_name(faction_sid: str) -> str

get_building_display_name(building: BuildingKey) -> str

get_unit_display_name(faction_sid: str, unit_sid: str) -> str

get_upgrade_display_name(faction_sid: str, upgrade_sid: str) -> str

get_milestone_display_name(milestone_id: str) -> str
```

The exact method names may follow repository naming conventions, but distinct entity categories must remain explicit.

### Inputs

Inputs are canonical identifiers or stable canonical identity objects.

Empty identifiers and invalid identity types raise clear programming or Query Layer request errors.

Localized strings are never valid lookup inputs.

### Outputs

Successful lookup always returns a non-empty display-ready string.

No public planner-display lookup returns `None`.

### Unknown canonical entity

When the supplied canonical identity is not present in canonical loaded game data, the Query Layer must raise its documented unknown-entity error.

The catalog is not responsible for pretending an invalid canonical identity exists.

### Known entity with missing localized text

When the canonical entity is valid but localized text is unavailable, lookup returns the deterministic fallback.

This is not a planner failure.

### Conflicting planner source

Conflicting text at the same approved source precedence is a catalog-construction error.

The implementation must not choose based on filesystem order.

## Fallback Policy

The mandatory fallback order is:

```text
1. localized planner name
2. canonical game-data display name, when available
3. canonical identifier
```

### Localized planner name

The first choice is text resolved through the Planner Localization Catalog's approved source policy for the requested language.

Empty localized text is treated as unavailable unless a specific entity contract explicitly permits an empty visible name. The initial implementation should require non-empty planner display output.

### Canonical game-data display name

The second choice is a canonical game-data display-name field associated with the valid entity, when one exists.

Examples may include:

- a canonical name field;
- an entity-owned display key rendered as stable source text;
- another approved canonical metadata field.

A raw localization key is not automatically a human-readable canonical display name. BE-014 must distinguish between a key reference and actual fallback text.

### Canonical identifier

The final fallback is a deterministic canonical identifier representation.

Recommended forms:

- faction: faction SID;
- building: building SID, with level included when required to distinguish identity;
- unit: unit SID;
- upgrade: upgrade SID;
- milestone: milestone ID.

Fallback formatting must be centralized in the catalog or its builder, not presenters.

### Identity preservation

Fallback never:

- changes the canonical object;
- writes localized text into canonical models;
- changes persistence documents;
- changes planner comparison keys;
- changes workspace selections;
- changes recruitment identities.

## Query Layer Integration

### Ownership

`PlanningQueryService` owns or references exactly one immutable `PlannerLocalizationCatalog` for its configured language.

Conceptually:

```text
PlanningQueryService
    _data: LoadedGameData
    _planner_localization: PlannerLocalizationCatalog
```

Existing explicit construction without planner localization may remain temporarily compatible where no display-name operation is used.

Canonical application startup should construct the planner catalog and provide it to the service.

### Public API

The Query Layer exposes planner display names through stable public operations.

Required categories:

```text
get_faction_display_text(faction_sid: str) -> str

get_building_display_text(building: BuildingKey) -> str

get_unit_display_text(faction_sid: str, unit_sid: str) -> str

get_upgrade_display_text(faction_sid: str, upgrade_sid: str) -> str
```

A milestone operation is additive when canonical milestone identities are implemented:

```text
get_milestone_display_text(milestone_id: str) -> str
```

Existing `get_building_display_text(...)` remains compatible in purpose but must delegate to the Planner Localization Catalog after BE-014.

### Query Layer validation

The Query Layer validates that requested identities exist in canonical loaded data before or as part of catalog resolution.

It translates catalog configuration failures into documented initialization failures rather than leaking repository paths or raw token dictionaries to application clients.

### Hidden implementation

The Query Layer must not expose:

- `PlannerLocalizationCatalog` token maps;
- localization file paths;
- source manifests;
- parser catalogs;
- raw localization SIDs;
- precedence rules.

The public result is the display-ready string.

### Discovery

Canonical discovery methods remain canonical:

```text
list_factions() -> tuple[str, ...]
list_buildings(...) -> tuple[str, ...]
```

ARCH-021 does not change these methods to return localized identity objects.

A future convenience projection may return immutable canonical-and-display pairs, but canonical identity must remain explicit and such an API requires normal public-contract review.

## Presenter and View Boundaries

### Presenters

Presenters:

- request display strings through Query Layer methods;
- build immutable presentation models;
- may cache complete immutable presentation projections when existing presenter architecture already permits it;
- invalidate presentation caches when language or catalog identity changes.

Presenters do not:

- import localization modules;
- read localization paths;
- parse files;
- build token dictionaries;
- implement fallback;
- normalize localization keys;
- select language resources.

### Views

Views receive display-ready strings.

Views do not:

- call localization APIs;
- access the Query Layer directly for localization;
- retain canonical-to-localized dictionaries;
- derive names from SIDs;
- apply fallback formatting.

Views may retain strings as part of immutable presentation state or widget rendering state.

## Loading Strategy

### Startup construction

The approved initial strategy is eager construction during canonical backend startup.

Sequence:

```text
1. load canonical game data
2. enumerate planner-visible canonical entities
3. resolve explicit planner localization sources for the selected language
4. index only those entities
5. validate source conflicts and policy
6. freeze PlannerLocalizationCatalog
7. construct PlanningQueryService
8. construct presenters and views
```

Benefits:

- initialization failures occur at a clear boundary;
- lookups are constant-time and side-effect free;
- no first-use file I/O occurs in presenters;
- catalog identity is stable for the service lifetime;
- deterministic tests can inspect one construction outcome.

### Lazy loading

Lazy file loading is not approved for BE-014.

A future implementation may lazily construct a whole immutable language catalog behind an application-owned language service, but individual lookups must not perform uncontrolled file scans or mutate a shared catalog.

### Cache ownership

The immutable catalog is the cache.

No second raw localization cache is required in presenters or views.

Parser-level temporary objects used during construction may be discarded after the planner catalog is frozen.

### Update semantics

The initial service treats the catalog as fixed for its lifetime.

Changing language or localization source creates a new immutable catalog and either:

- a new `PlanningQueryService`; or
- an atomically replaced application-level localization context under a separately approved language-switching design.

In-place catalog mutation is not approved.

## Thread Safety

After construction, catalog operations are read-only.

The contract requires safe concurrent reads provided the underlying immutable mappings are not mutated.

Catalog construction itself need not be thread-safe because it occurs before publication.

ARCH-021 does not authorize background loading or asynchronous initialization.

## Language Support

The catalog has an explicit language identifier.

Adding another language requires:

- an approved source policy or provider for that language;
- the same canonical planner entity allowlist;
- the same deterministic fallback rules;
- validation for missing and conflicting entries;
- no planner or presenter redesign.

Language is presentation configuration and must not enter planner inputs or persisted planning scenarios.

A future user preference may persist language separately as application configuration, not scenario identity.

## DLC and Content Expansion

New factions, buildings, units, and upgrades integrate through canonical data expansion.

At construction time, the catalog builder enumerates the new canonical entities and resolves their display sources according to the configured policy.

Required behavior:

- missing localized text falls back deterministically;
- unsupported or malformed source configuration fails clearly;
- existing entity names remain unchanged for identical inputs;
- source order remains explicit;
- no presenter dictionary changes are required.

DLC-specific localization files may be added to explicit planner source policies.

The implementation must not scan every DLC interface resource.

## Alternate Display-Name Sources

The catalog architecture permits alternate providers, including:

- game localization documents;
- canonical game-data text;
- planner-owned resources for planner-defined milestones;
- test fixtures;
- future language packs.

All providers must resolve the same canonical planner identities and obey one deterministic precedence policy.

Provider interfaces are internal implementation details unless separately promoted to public API.

## Failure Model

Recommended construction failures include:

```text
PlannerLocalizationError
PlannerLocalizationSourceError
PlannerLocalizationConflictError
```

Exact exception names are delegated to BE-014.

Failures must distinguish:

- malformed source;
- unsupported language;
- ambiguous source policy;
- conflicting text at equal precedence;
- invalid planner-entity association.

Missing optional localized text is not a construction failure because fallback is mandatory.

Public Query Layer lookup failures should remain Query Layer errors for invalid canonical requests.

## Compatibility

ARCH-021 is additive.

It preserves:

- existing canonical models;
- existing parser contracts;
- duplicate-key validation;
- planner algorithms;
- Query Layer ownership;
- scenario persistence;
- Planning Workspace semantics;
- Scenario Comparison semantics;
- existing display-name callers.

`PlanningQueryService.from_default_game_data()` remains the canonical convenience constructor. BE-014 may change its internal localization construction from one parsed city file to the Planner Localization Catalog while preserving its public call shape.

Existing `PlanningQueryService(loaded_data)` construction may remain valid for non-presentation tests and callers. Display-name operations without a configured planner catalog must either:

- apply canonical fallback from loaded data; or
- raise the existing documented configuration error.

BE-014 must choose and document one deterministic compatibility behavior. Canonical application startup must always configure the catalog.

## Prohibited Designs

ARCH-021 does not authorize:

- changing existing parser duplicate-key semantics;
- suppressing conflicting duplicate keys;
- “first file wins” behavior;
- “last file wins” behavior;
- parsing the complete localization directory as the planner catalog;
- localized names stored in canonical models as identity;
- handwritten dictionaries of game entity names;
- presenters parsing or indexing localization;
- views performing localization lookup;
- planner algorithms formatting display names;
- persisted scenarios storing localized names instead of canonical identifiers;
- raw localization maps exposed through Query Layer APIs;
- lookup-time filesystem scanning;
- mutable catalogs shared with presentation code.

## BE-014 Implementation Guidance

BE-014 should:

1. introduce `PlannerLocalizationCatalog` and its builder;
2. define explicit planner entity indexes;
3. define an explicit source policy for the initial language;
4. enumerate planner entities from `LoadedGameData`;
5. reuse existing parser behavior only for compatible source units;
6. reject equal-precedence planner-name conflicts;
7. implement the mandatory fallback order;
8. construct the catalog eagerly at startup;
9. integrate it into `PlanningQueryService`;
10. retain `get_building_display_text(...)`;
11. add faction, unit, and upgrade display-name operations;
12. keep raw storage private;
13. add deterministic fixtures that include reused localization keys in unrelated files;
14. demonstrate that unrelated localization resources are not scanned.

Recommended module placement:

```text
olden_db/
    localization.py
    planner_localization.py
    query.py
```

`localization.py` retains existing parser semantics.

`planner_localization.py` owns planner-specific source policy, indexing, fallback, and immutable lookup.

Exact filenames may evolve, but ownership must remain separate.

## Required Validation

BE-014 must validate:

- existing localization parser tests remain unchanged and pass;
- conflicting duplicate keys still raise through existing parser contracts;
- the planner catalog does not scan the complete localization directory;
- only canonical planner entities are indexed;
- faction display lookup;
- building display lookup across levels and upgrades;
- base-unit and upgraded-unit lookup;
- recruitment display lookup through canonical unit identity;
- milestone lookup when milestone identities are available;
- localized-name success;
- canonical game-data fallback;
- canonical identifier fallback;
- invalid canonical identity failure;
- deterministic repeated construction;
- deterministic repeated lookup;
- equal-precedence conflict failure;
- immutable catalog state;
- safe repeated concurrent reads;
- Query Layer-only presenter access;
- passive views;
- scenario persistence continues to store canonical identity;
- planner output is unchanged by localization configuration;
- complete UI-011 startup succeeds without full-directory localization parsing.

## Migration Strategy

### Phase 1 — Catalog foundation

- introduce catalog identity and immutable indexes;
- introduce deterministic fallback helpers;
- add source-policy fixtures;
- preserve all parser tests.

### Phase 2 — Building compatibility

- populate faction and building indexes;
- redirect existing `get_building_display_text(...)`;
- preserve current desktop summary behavior;
- validate fallback equivalence.

### Phase 3 — Unit and recruitment support

- populate unit and upgrade indexes from canonical unit families;
- expose Query Layer operations;
- migrate recruitment presenters away from raw identifiers where display text is required.

### Phase 4 — UI-011 resumption

- construct the complete planner catalog during startup;
- provide display-ready immutable presentation values;
- verify no raw localization access in presenters or views;
- resume UI-011.

### Phase 5 — Additional languages and entities

- add source policies and data;
- add canonical entity categories only when planner-visible;
- preserve catalog and Query Layer ownership.

## Decision Consequences

### Benefits

- parser integrity is preserved;
- full-directory duplicate conflicts no longer block planner startup;
- canonical identities remain authoritative;
- every planner feature uses one display-name source;
- presenters and views remain isolated from localization storage;
- fallback behavior is deterministic;
- additional languages and content are data expansions;
- localization does not alter planner behavior.

### Costs

- backend startup gains an explicit catalog-construction stage;
- source policies require maintenance as game content evolves;
- entity categories require canonical discovery and typed lookup;
- Query Layer gains several additive display-name operations;
- tests must cover source filtering and fallback separately from parser behavior.

## Acceptance

ARCH-021 is satisfied when repository documentation establishes:

- unchanged parser responsibility;
- one authoritative Planner Localization Catalog;
- explicit planner-entity scope;
- canonical identity preservation;
- deterministic lookup and fallback;
- immutable eager loading;
- Query Layer ownership;
- passive presentation boundaries;
- BE-014 implementation and validation requirements;
- sufficient support for UI-011 without further architectural redesign.

## BE-014 Realization

BE-014 realizes this architecture with `planner_localization.py`. Canonical startup uses the explicit English `cities.json` planner source rather than directory parsing. Existing parser duplicate semantics are unchanged. Temporary dictionaries exist only during construction; the published catalog uses immutable mappings and performs no lookup-time I/O or mutation.

