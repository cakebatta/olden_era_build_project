# Economy Timeline Desktop Presentation

## Authoritative Source

The Economy Timeline is rendered from one immutable `ResourceLedger` returned
by:

```text
PlanningQueryService.generate_resource_ledger(...)
```

The desktop does not request or calculate an `IncomeTimeline`, build plan,
recruitment stock, income activation, upgrade replacement, balances, or totals
separately.

## Daily Ordering

Each dated section preserves the backend-certified accounting order:

1. beginning-of-day town income;
2. construction spending;
3. recruitment spending;
4. closing daily balance.

Income entries are displayed only when the ledger supplies them. Dates without
income do not receive artificial zero-income rows.

## Income Presentation

Every income entry retains its source `BuildingKey` and nonzero resource
amounts. Canonical identity remains visible. A future public localization path
may add supplementary names without replacing canonical identity.

Income is visually distinguished with an explicit positive sign and remains
separate from spending totals.

## Summary

The Economy Summary displays authoritative ledger fields:

- construction total;
- recruitment total;
- combined spending;
- income total;
- ending balance;
- feasibility;
- first-deficit facts.

`combined_total` remains construction plus recruitment spending only. Income is
not subtracted from or merged into that field.

## Deficits

The first-deficit date, resource, signed balance, and positive magnitude are
displayed directly from `ResourceDeficit`.

A triggering event is displayed only when the desktop can reconstruct the
complete certified event-index sequence, including income, construction, and
recruitment entries. The desktop must omit the trigger rather than guess from an
incomplete sequence.

## Scenarios and Scope

Canonical and edited starting-building scenarios flow through the existing
ledger request. Scenario-dependent town income therefore appears automatically
from the returned ledger without desktop special cases.

Only deterministic town income represented in the ledger is displayed.
External income sources, map pickups, marketplace activity, and recommendations
remain excluded.
