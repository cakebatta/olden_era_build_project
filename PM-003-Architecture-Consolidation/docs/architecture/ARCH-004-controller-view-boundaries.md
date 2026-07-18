# ARCH-004 – Controller and View Responsibilities

Status: Approved

Controllers own workflow, orchestration, and session coordination.
Views own rendering and ephemeral UI state only.
Views never execute business rules or persistence operations.
