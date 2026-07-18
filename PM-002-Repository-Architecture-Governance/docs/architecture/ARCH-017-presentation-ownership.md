# ARCH-017 – Presentation Ownership and Responsibility Boundaries

Status: Approved

## Principle
Every piece of information has one authoritative owner. Other layers may project or format it but must not redefine its meaning.

## Domain
Owns business rules, planner logic, validation, deterministic outputs.

## Query Layer
Owns read-only projections.

## Controller/Presenter
Owns orchestration and immutable presentation models.
May add presentation defaults that do not alter domain semantics.

## View
Owns rendering and ephemeral UI state only.

## Engineering
Implement against ADRs. Request Architecture Clarification if ownership is unclear.

## QA
Certify against work orders, documentation, and ADRs.
Report Architecture Ambiguities rather than inventing architectural rules.

## PM
Resolve ambiguities through new or updated ADRs.
