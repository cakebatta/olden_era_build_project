# Team Handoff Protocol

## Purpose

This document defines the standard communication, synchronization, responsibility, and verification protocol for all specialized project roles.

GitHub is the canonical source of truth. Conversation history may provide context, but repository documentation defines current project standards.

## Documentation Synchronization (Mandatory)

Before every assigned task, all team members—including the Project Manager—must:

1. Pull or otherwise inspect the latest authoritative `main` branch.
2. Review the entire `docs/` directory for new or modified documentation.
3. Review all active architecture decisions and approved architecture change records.
4. Review this handoff protocol and any role-specific onboarding instructions.
5. Treat repository documentation as authoritative over prior chat guidance.
6. Begin work only after synchronization.

If repository access is temporarily limited, the team member must:

1. Use all verifiable repository evidence available.
2. Distinguish confirmed findings from provisional findings.
3. State the access limitation explicitly.
4. Continue as far as the available evidence permits.
5. Never invent or assume repository state.

## Repository Baseline

The GitHub `main` branch defines the engineering baseline.

Engineers must develop against the current repository state. QA certification, Architecture review, and Project Manager acceptance record project quality and release readiness, but they do not redefine what code exists or require engineers to work against an older conceptual baseline.

When governance records lag behind repository history, the governance records must be reconciled to the repository rather than asking Engineering to disregard `main`.

## Work Order Structure

Every Project Manager work order should include, in proportion to the size and risk of the assignment:

1. Documentation Synchronization
2. Task Identifier
3. Objective
4. Background
5. Scope
6. Constraints
7. Deliverables
8. Success Criteria
9. Runtime Verification Requirements
10. Dependencies and Next Owner
11. Suggested Git Commit Title
12. Suggested Git Commit Body

Major features, architectural changes, cross-team work, and governance changes should receive full work orders. Small corrective or incremental assignments may use a shorter format provided that scope, constraints, validation, and ownership remain clear.

## Standard Task Completion Package

Every completed task must include:

### 1. Task Identifier

Reference the assigned milestone and task.

### 2. Completion Status

Use: Complete, Complete with Notes, Blocked, or Requires Review.

### 3. Summary

Describe the capability added, changed, or verified.

### 4. Deliverables

List modules, scripts, documentation, tests, configuration, assets, or generated artifacts.

### 5. Files Added

List every new file, or state `None`.

### 6. Files Modified

List every modified file, or state `None`.

### 7. Installation or Setup Requirements

Document required setup, or state `None`.

### 8. Validation Performed

Describe automated checks, static checks, representative outputs, architectural checks, and any manual validation performed by the Project Owner.

### 9. Validation Commands

All terminal-level Python commands must use module execution:

```text
python -m scripts.example
```

Do not use:

```text
python scripts/example.py
```

Editable installation with `-e` is not assumed to work across environments.

### 10. Expected Validation Output

Describe expected success messages, generated files, row counts, deterministic results, or interaction behavior.

### 11. Architectural Notes

State whether parser, planner, graph, database, public API, Query Layer, UI boundaries, canonical identifiers, localization behavior, or documented ownership changed.

### 12. Known Limitations

Document intentional omissions, deferred issues, unverified runtime behavior, and risks, or state `None`.

### 13. Suggested Git Commit

For every repository change, include a concise commit title and explanatory body.

If no files changed, state that no commit is required.

Do not request a commit hash from another role.

### 14. Message to the Project Manager

Confirm acceptance criteria, risks, architectural concerns, recommended next owner, and next task.

## Runtime Verification Policy

Runtime verification is performed collaboratively by the Project Owner and the implementing engineer.

The implementing Backend or UI Engineer must provide:

1. Exact commands to execute.
2. Required setup or starting state.
3. A concise sequence of runtime scenarios.
4. Expected behavior for each scenario.
5. Any logs, screenshots, or outputs that should be returned for diagnosis.

The Project Owner must:

1. Run the application and commands locally.
2. Perform the requested visual or interactive checks.
3. Return the observed results.
4. Work with the implementing engineer to diagnose failures.
5. Confirm whether runtime behavior is acceptable.

The Project Manager uses the returned runtime results when making the final acceptance decision.

QA does not independently execute or certify runtime application behavior. QA may identify runtime risks and provide a concise list of behaviors that require manual verification, but the implementing engineer owns the executable validation instructions.

Static inspection, automated execution, and manual runtime verification must always be distinguished.

## Validation Philosophy

Use executable automated validation for architectural and behavioral contracts where practical.

Use source inspection only where execution is impractical or where the requirement is inherently structural.

Use representative human validation for rendering, interaction, platform behavior, and user experience.

Tests must verify the behavior or boundary they claim to cover. Source-token assertions must not be presented as equivalent to runtime or executable integration tests.

## Role Responsibilities

### Project Manager

Owns:

- roadmap and priorities;
- task sequencing and scope;
- cross-role coordination;
- acceptance decisions;
- governance rules;
- documentation requirements;
- runtime verification coordination;
- authorization of dependent work.

The Project Manager does not implement production code unless explicitly acting in another assigned role.

### Architecture Engineer

Owns:

- architectural consistency;
- architecture decision records;
- architecture change records;
- canonical architecture documentation;
- repository architecture governance;
- long-term structural maintainability;
- clarification of ambiguous architectural ownership.

The Architecture Engineer must distinguish repository fact, inference, recommendation, and unresolved ambiguity.

### Backend Engineer

Owns:

- domain logic;
- planner behavior;
- backend interfaces;
- Query Layer implementation;
- backend tests;
- focused backend validation;
- runtime commands for backend changes.

### Data Engineer

Owns:

- game-data interpretation;
- asset validation;
- data correctness;
- assumptions;
- discrepancy classification;
- source-data documentation.

### UI Engineer

Owns:

- desktop presentation;
- interaction design;
- presenter and view implementation;
- UI-focused tests;
- accessibility implementation;
- usability;
- runtime commands and scenarios for UI changes.

The UI Engineer must not bypass backend or Query Layer boundaries.

### QA Engineer

Owns:

- independent static certification;
- regression review;
- architectural and ownership boundary review;
- test and coverage assessment;
- repository hygiene review;
- documentation review;
- identification of runtime behaviors requiring manual verification.

QA does not certify live rendering, mouse behavior, keyboard behavior, platform-specific appearance, or other runtime application behavior.

### Project Owner

Acts as the communication link between roles, runs requested local verification, returns results, uploads or pushes approved changes, and confirms product behavior.

## Product-First Development

Engineering, architecture, testing, and governance exist to support a useful player experience.

Infrastructure or governance work should be placed on the critical path only when it is necessary for correctness, safety, maintainability, or delivery of a planned capability.

When choosing between technically acceptable approaches, prefer the option that:

1. Supports the intended player workflow.
2. Preserves established boundaries.
3. Avoids unnecessary complexity.
4. Leaves room for foreseeable product evolution.
5. Can be validated clearly.

Architectural refinement must not become an end in itself.

## Product Design Principle — Interaction Independence

The application architecture must model player intent rather than a particular interaction mechanism.

Planning-related components should communicate semantic concepts such as:

- planning selections;
- selected buildings;
- active city plans;
- planning workspace state;
- planner requests.

They must not encode assumptions that those concepts originate from:

- checkboxes;
- drag-and-drop;
- tree controls;
- context menus;
- search panels;
- keyboard shortcuts;
- any future interaction mechanism.

The current desktop application may use checkboxes because they are simple, reliable, and independent of unavailable or uncertain visual assets. That is a presentation decision, not an architectural contract.

Future UI revisions should be able to replace the interaction mechanism without requiring changes to planner logic, domain models, Query Layer contracts, or other backend boundaries.

Before introducing or reviewing planning functionality, ask:

> Does this change represent what the player wants to build, or merely how today's UI captures that choice?

Architectural decisions should favor player intent over interaction implementation.

## Public API and Boundary Reviews

For boundary changes, QA and Architecture should assess:

- Which modules clients may import
- Which types form the public contract
- Whether internal state is exposed
- Whether clients can bypass the intended interface
- Whether future refactoring would break clients
- Whether automated boundary enforcement is needed

Operational success alone is not sufficient for architectural certification.

## Definition of Done

A task is complete only when:

- Assigned work is complete.
- Documentation synchronization occurred.
- Acceptance criteria were addressed.
- Validation commands were supplied.
- Local verification was run when applicable.
- Results were reviewed.
- The completion package was delivered.
- Documentation updates were identified or completed.
- Commit title and body were provided when files changed.
- The Project Manager approved the work.
- The next dependent task was identified.

No dependent task should begin before Project Manager authorization.
