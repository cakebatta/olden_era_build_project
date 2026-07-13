# Team Handoff Protocol

## Purpose

This document defines the standard communication protocol between
specialized engineering roles.

Every implementation task should conclude with a structured handoff
package so that work can be reviewed, validated, and approved
consistently.

This protocol exists to improve project clarity rather than introduce
unnecessary process.

------------------------------------------------------------------------

# Standard Task Completion Package

Every completed implementation task should include the following
sections.

## 1. Task Identifier

Reference the assigned task.

Example:

-   BE-002 --- CSV Validation Export

------------------------------------------------------------------------

## 2. Completion Status

Clearly indicate one of:

-   Complete
-   Complete with Notes
-   Blocked
-   Requires Review

------------------------------------------------------------------------

## 3. Summary

Provide a concise description of what was implemented.

This should describe the capability added rather than the implementation
details.

------------------------------------------------------------------------

## 4. Deliverables

List all significant outputs.

Examples:

-   New modules
-   New scripts
-   Documentation
-   Tests
-   Configuration
-   Assets

------------------------------------------------------------------------

## 5. Files Added

List every newly created file.

Example:

``` text
src/export/csv_export.py
scripts/export_validation.py
docs/export_validation.md
```

------------------------------------------------------------------------

## 6. Files Modified

List every modified file.

Example:

``` text
src/database.py
src/planner.py
```

------------------------------------------------------------------------

## 7. Installation or Setup Requirements

If additional setup is required, document it.

If no setup is required, explicitly state:

> None.

------------------------------------------------------------------------

## 8. Validation

Describe how the implementation was verified.

Include:

-   Validation scripts executed
-   Manual verification performed
-   Representative outputs inspected

------------------------------------------------------------------------

## 9. Validation Commands

Provide every command necessary to reproduce the validation.

Example:

``` text
python scripts/export_validation.py
pytest
```

------------------------------------------------------------------------

## 10. Expected Validation Output

Describe what reviewers should expect.

Examples:

-   CSV files generated
-   Tests passing
-   No exceptions
-   Expected row counts

Avoid copying large outputs.

------------------------------------------------------------------------

## 11. Architectural Notes

Document any architectural considerations.

Examples:

-   Public APIs preserved
-   No parser behavior changed
-   No planner logic changed
-   No breaking changes
-   New extension points introduced

------------------------------------------------------------------------

## 12. Known Limitations

Document any intentional omissions or remaining work.

If none exist, state:

> None.

------------------------------------------------------------------------

## 13. Suggested Git Commit

### Commit Title

Provide a concise commit title.

### Commit Body

Provide a short explanatory body describing the purpose of the change.

------------------------------------------------------------------------

## 14. Message to the Project Manager

End every implementation task with a short summary addressed to the
Project Manager.

Include:

-   Confirmation that acceptance criteria were satisfied
-   Outstanding risks
-   Architectural concerns
-   Recommendations for the next milestone

This section is intended to support milestone review rather than
implementation.

------------------------------------------------------------------------

# Responsibilities

## Implementation Engineers

Responsible for completing every section of the Standard Task Completion
Package.

## Project Manager

Responsible for:

-   Reviewing architectural consistency
-   Approving or rejecting the implementation
-   Determining whether documentation requires updates
-   Authorizing the next task

## QA Engineer

Responsible for validating implementation correctness, not architectural
direction.

## Data Engineer

Responsible for verifying correctness of game data and assumptions, not
implementation details.

------------------------------------------------------------------------

# Definition of Done

A task is not considered complete until:

-   Implementation is complete.
-   Validation has been performed.
-   The Standard Task Completion Package has been delivered.
-   The Project Manager has reviewed the implementation.
-   QA has completed verification when required.
-   Any required documentation updates have been identified.

Only after these conditions are met may the next dependent task begin.
