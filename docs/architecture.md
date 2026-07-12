# Olden Era Build Planner - Architecture

## Purpose
Build a deterministic planning engine for Heroes of Might & Magic: Olden Era tournament play.

The application models:
- Building prerequisites
- Resource costs
- Construction timing (one building per day)
- Recruitment costs
- Multiple legal build orders
- Localized display names

It intentionally does **not** model random map income.

## Core Modules

- `models.py` — shared data structures.
- `constants.py` — shared constants.
- `paths.py` — canonical project paths.
- `parser.py` — parses city/building logic.
- `unit_parser.py` — parses unit logic.
- `database.py` — assembles a connected in-memory database.
- `graph.py` — dependency graph + all topological orders.
- `planner.py` — dated build plans and cumulative costs.
- `localization.py` — SID → display text.
- `csv_export.py` — validation exports (checkpoint).

## Design Principles

1. SIDs are canonical identifiers.
2. Localization is presentation only.
3. Every parser is reusable and path-agnostic.
4. `paths.py` is the only module aware of the repository layout.
5. Every feature should have an accompanying test.
