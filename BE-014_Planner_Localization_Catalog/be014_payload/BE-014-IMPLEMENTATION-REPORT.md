# BE-014 — Planner Localization Catalog

## Status

Implementation complete; Project Owner executable/runtime verification pending.

## Objective

Implement the immutable planner-scoped localization catalog authorized by ARCH-021 without changing canonical identity, planner algorithms, persistence, comparison contracts, or desktop presentation.

## Production Deliverables

- `olden_db/olden_db/planner_localization.py`
- Immutable faction, building, unit, and upgrade indexes
- Explicit English planner-localization source selection through `cities.json`
- Eager Query Layer construction
- Constant-time lookup operations
- Compatibility aliases for existing display-text callers
- Deterministic canonical fallback

## Source Policy

Canonical startup parses only `Core/Lang/english/texts/cities.json`. It does not parse or scan the complete localization directory. Catalog indexing begins from canonical planner-visible entities in `LoadedGameData`; unrelated UI tokens are not copied into planner indexes.

## Fallback

Resolution order is localized planner name, canonical game-data display name when an approved human-readable field exists, then canonical identifier.

## Validation

Run from `olden_db`:

```text
python -m scripts.test_planner_localization_catalog
python -m scripts.test_localization
python -m scripts.test_query_layer
python -m scripts.test_build_plan_comparison_service
```
