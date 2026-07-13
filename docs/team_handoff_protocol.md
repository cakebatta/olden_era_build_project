# Team Handoff Protocol

## Purpose

This document defines the standard communication and verification protocol for all specialized project roles.

GitHub is the canonical source of truth. Conversation history provides context, but repository documentation defines current project standards.

## Documentation Synchronization (Mandatory)

Before every assigned task, all team members—including the Project Manager—must:

1. Pull the latest repository.
2. Review the entire `docs/` directory for new or modified documentation.
3. Treat repository documentation as authoritative over prior chat guidance.
4. Begin work only after synchronization.

## Work Order Structure

Every Project Manager work order should include:

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
Describe scripts, manual checks, representative outputs, regression checks, and architectural checks.

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
State whether parser, planner, graph, database, public API, Query Layer, UI boundaries, canonical identifiers, or localization behavior changed.

### 12. Known Limitations
Document intentional omissions, deferred issues, and risks, or state `None`.

### 13. Suggested Git Commit

For every repository change, include a concise commit title and explanatory body.

If no files changed, state that no commit is required.

### 14. Message to the Project Manager
Confirm acceptance criteria, risks, architectural concerns, recommended next owner, and next task.

## Runtime Verification Policy

Engineering chats may be unable to execute the local repository.

Therefore:

1. Engineers provide exact verification commands.
2. The Project Owner runs them locally.
3. The Project Owner returns the results.
4. Final certification accounts for those results.
5. Static inspection and runtime verification must be distinguished.

## Validation Philosophy

Use representative human validation and exhaustive automated validation where practical.

## Role Responsibilities

### Project Manager
Owns milestones, task order, architecture, ownership, acceptance, documentation requirements, commit recommendations, and authorization of dependent work.

### Backend Engineer
Owns backend algorithms, interfaces, query services, implementation, and focused backend validation.

### Data Engineer
Owns game-data interpretation, asset validation, data correctness, assumptions, and discrepancy classification.

### UI Engineer
Owns interaction, presentation, formatting, UI workflow, accessibility, and usability. Must not bypass backend boundaries.

### QA Engineer
Owns regression review, runtime verification requirements, boundary review, coverage assessment, and independent certification.

### Project Owner
Acts as communication link, runs requested local verification, returns results, pushes approved changes, and confirms product behavior.

## Public API and Boundary Reviews

For boundary changes, QA should assess:

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
