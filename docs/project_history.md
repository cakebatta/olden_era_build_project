# Project History

## Purpose

This document records major project milestones and the architectural decisions behind them.

## Phase I — Backend Foundation

**Status:** Complete

Completed:
- Canonical data models
- Building parser
- Unit parser
- Localization
- Dependency graph
- Planner
- Integrated database
- Centralized path management
- Backend validation scripts

Key decisions:
- GitHub is the canonical source of truth.
- SIDs are the only canonical internal identifiers.
- Validation precedes feature expansion.
- Backend, UI, Data, QA, and Project Management have distinct ownership.

## Sprint 1 — Validation Layer

**Status:** Complete

Objective:
Make the backend observable and trustworthy.

Completed:
- Deterministic CSV validation exports
- Human validation workflow
- Cross-machine deterministic export artifacts
- Regression validation

## Sprint 2 — Query Layer

**Status:** Complete

Objective:
Provide a stable public backend interface.

Completed:
- PlanningQueryService
- Canonical initialization
- CLI engineering playground
- Backend state encapsulation
- Discovery APIs
- Architectural certification
- Version 1.0 public contract

Key decisions:
- Query Layer is the supported client interface.
- Stable domain objects are part of the public API.
- Internal backend modules remain implementation details.

## Version 1.0 Freeze

The Query Layer Version 1.0 is considered architecturally stable.

Future backend work should preserve documented public contracts while allowing internal implementation to evolve.

## Next Phase

Sprint 3 will focus on Desktop Application Architecture and UI implementation.

## Guiding Principles

- Trustworthiness over feature count
- Deterministic behavior
- Explicit architecture
- Incremental milestones
- Documentation of intent
- Stable public interfaces
