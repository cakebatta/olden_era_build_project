# ARCH-001 – Domain Boundaries

Status: Approved

The Domain layer owns all game rules, deterministic planning, validation, resource calculations,
graph algorithms, and immutable domain models. Domain code must not contain UI or presentation logic.
