# BE-011 — Planning Summary Support Contracts

## Completion Status

Complete with Project Owner runtime verification pending.

## Repository Baseline

- Repository: `cakebatta/olden_era_build_project`
- Branch: `main`
- Baseline commit: `7d47f3d0cbac92d0814cd7f54fd9f972fa9f0b5a`

## Summary

This additive change extends the authoritative `PlannerResult` with an immutable
daily construction-cost projection and adds a Query Layer localization
operation accepting canonical `BuildingKey` identity.

The daily schedule is derived from the already accepted `BuildPlan.steps` while
constructing `PlannerResult`. It requires no additional graph traversal, planner
execution, Query Layer request, or workspace lifecycle.

## Files Modified by the Application Utility

- `olden_db/olden_db/planner.py`
- `olden_db/olden_db/query.py`
- `docs/query_layer.md`

## Files Added

- `olden_db/scripts/test_planning_summary_support.py`

## Application Instructions

Extract this package over the repository root, then run:

```text
python apply_be_011.py
```

The utility verifies exact baseline source blocks before changing them and
refuses to proceed when the repository does not match the reviewed baseline.
After reviewing the changes, remove `apply_be_011.py`; it is a delivery utility,
not canonical production code.

## Validation Commands

Run from the repository's `olden_db` directory:

```text
python -m scripts.test_planning_summary_support
python -m scripts.test_planning_workspace
python -m scripts.test_planner_diagnostic_pipeline
```

Then run the existing complete backend certification suite.

## Expected New Validation Output

```text
PASS: test_daily_schedule_is_deterministic_and_matches_plan
PASS: test_planner_result_constructor_remains_compatible
PASS: test_query_layer_localization_uses_canonical_identity
PASS: test_existing_query_service_constructor_and_planner_behavior_remain_valid
PASS: 4 planning summary support checks
```

## Architectural Notes

- Planner traversal and ordering behavior are unchanged.
- Dependency graph behavior is unchanged.
- Workspace lifecycle and revision behavior are unchanged.
- Scenario semantics are unchanged.
- Presenter architecture is unchanged.
- Existing `generate_build_plan(...)` remains unchanged.
- Existing `generate_planner_result(...)` arguments remain unchanged.
- Existing one-argument `PlanningQueryService(loaded_data)` construction remains valid.
- Localization internals remain behind the Query Layer.
- The schedule is immutable and belongs to the same `PlannerResult` lifecycle.

## Known Limitation

The environment could inspect the authoritative repository but could not clone
it because command-line GitHub DNS resolution was unavailable. The safe
application utility and new test script were syntax-checked, but full repository
execution must be performed locally.

## Suggested Commit

Summary:

```text
Add planning summary support contracts
```

Description:

```text
Extend PlannerResult with an immutable daily construction-cost schedule derived
from the accepted build plan without additional planner execution.

Add a Query Layer operation for resolving localized building display text from
canonical BuildingKey identity while preserving existing planning APIs,
workspace lifecycle, and deterministic planner behavior.
```
