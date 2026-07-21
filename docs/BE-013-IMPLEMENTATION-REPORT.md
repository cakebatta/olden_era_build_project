# BE-013 — Build Plan Comparison Service

## Status

Implementation complete; Project Owner executable verification pending.

## Repository Baseline

- Repository: `cakebatta/olden_era_build_project`
- Branch: `main`
- Baseline commit: `f75e62795ec10990137cc69c7d01cb9b4113ddde`

## Public Boundary

`PlanningQueryService.compare_accepted_build_plans(left, right)` compares two
existing accepted `PlannerResult` values. It performs no planning, graph
construction, scenario loading, diagnostics, persistence, or unrelated Query
Layer calls.

The historical `PlanningQueryService.compare_plans(...)`,
`PlanComparison`, and `compare_build_plans(...)` contracts remain unchanged.

## Alignment Semantics

The service computes a deterministic longest common subsequence over complete
`BuildingKey` values, including resulting building level.

Matched identities are emitted as `MATCHED`. Unmatched chronological runs
between matches are paired left-to-right as `DIFFERENT`; any remainder is
emitted as `LEFT_ONLY` or `RIGHT_ONLY`. This preserves source ordering, repeated
building upgrades, and deterministic tie handling without inventing actions.

## Delta Semantics

Every signed delta uses:

`delta = right - left`

Therefore:

- positive completion delta means right completes later;
- negative completion delta means right completes earlier;
- positive step delta means right has more construction actions;
- every resource component is right cost minus left cost.

## Failures

Expected unavailable states are immutable typed outcomes:

- missing left accepted plan;
- missing right accepted plan;
- invalid left plan data;
- invalid right plan data.

An accepted empty plan remains valid.

## Validation

From `olden_db`:

```text
python -m scripts.test_build_plan_comparison_service
python -m scripts.test_query
python -m scripts.test_planning_workspace
python -m scripts.test_scenario_comparison_collection
python -m scripts.test_planning_summary_support
python -m scripts.test_build_plan_timeline
python -m scripts.test_planner_diagnostic_pipeline
```

Expected new-suite result:

```text
PASS: test_identical_and_immutable
PASS: test_divergence_repeated_upgrades_and_exclusive_order
PASS: test_empty_and_signed_deltas
PASS: test_swap_and_determinism
PASS: test_typed_missing_failures
PASS: test_public_query_access_and_no_regeneration
PASS: 6 build plan comparison service checks
```
