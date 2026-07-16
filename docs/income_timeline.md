# Income Timeline Domain

## Purpose

`BuildingLevel.income` is an authoritative asset-derived amount vector. It does
not define when income is produced. The Income Timeline domain applies the
Project Owner's deterministic gameplay timing assumptions to an existing
`FactionCity` and `BuildPlan`.

The domain produces immutable, dated facts only. It does not calculate resource
balances, construction spending, recruitment spending, feasibility, scenario
resolution, recommendations, or presentation strings.

## Public Contracts

- `IncomeEvent`: one nonzero source-building amount on one date;
- `DailyIncome`: every source event and their aggregate for one evaluated date;
- `IncomeTimeline`: the complete inclusive interval, flat source events, daily
  records, and total income;
- `calculate_income_timeline(...)`: pure calculation entry point.

`daily_income` includes every evaluated date, even when no income is produced.
The flat `events` tuple includes only nonzero events.

## Starting-State Semantics

The domain uses the project-wide effective starting-state contract:

- `starting_buildings=None` derives canonical `constructed_on_start` keys;
- `starting_buildings=frozenset()` means explicitly no starting buildings;
- an explicit nonempty `frozenset[BuildingKey]` is authoritative.

The Income Timeline does not import or resolve `PlanningScenario`.

An income-producing building in the effective starting state is active on
`plan.starting_date`.

## Construction and Upgrade Timing

A building completed on date D becomes income-active on D + 1.

When a higher level of a building SID completes, the previously active lower
level still produces on the construction date. The higher level replaces it on
the following day.

For each SID, only the highest active level determines income. Levels never
stack. A zero-income higher level may therefore replace a lower level and
produce no event.

Separate income-producing SIDs combine normally.

## Ordering and Totals

Daily records appear chronologically from `starting_date` through
`through_date`, inclusive. Events within a date use canonical `BuildingKey`
ordering.

Each daily total is the sum of that day's source events. `total_income` is the
sum of all daily totals. Existing immutable `ResourceCost` arithmetic is used.

## Boundaries

The domain does not:

- modify balances;
- process construction or recruitment costs;
- determine feasibility;
- model pickups, mines, optional effects, or income modifiers;
- change parser, planner, graph, Recruitment Stock, Resource Ledger, Query
  Layer, or UI behavior.
