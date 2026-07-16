# Resource Ledger

## Purpose

The Resource Ledger composes three independent, immutable backend domains:

- `BuildPlan` supplies dated construction actions and construction costs;
- `IncomeTimeline` supplies certified dated town-income events;
- `RecruitmentStock` supplies dated creature availability.

The ledger applies these facts to one explicit starting `ResourceCost` and
returns deterministic financial entries, balances, totals, feasibility, and
first-deficit information.

The ledger does not calculate construction order, income activation, building
upgrade replacement, creature growth, wall modifiers, or scenario semantics.

## Canonical Daily Accounting Order

For every evaluated date, the Resource Ledger processes:

1. beginning-of-day `IncomeTimeline` events in their certified canonical order;
2. same-day construction and its cost;
3. recruitment actions and their costs;
4. the end-of-day resource balance.

Income can therefore fund construction or recruitment occurring later on the
same date.

## Income Contracts

`IncomeLedgerEntry` retains:

- the event date;
- the source `BuildingKey`;
- the complete income `ResourceCost`;
- the balance immediately after that source event.

`ResourceLedger` additionally retains:

- the supplied `IncomeTimeline`;
- all applied `income_entries`;
- aggregate `income_total`.

`construction_total`, `recruitment_total`, and `combined_total` retain their
existing spending semantics. `combined_total` remains construction spending
plus recruitment spending; income is not subtracted from that factual expense
total. Income instead affects dated and ending balances.

## Input Consistency

When an `IncomeTimeline` is supplied:

- its faction must match city, plan, and Recruitment Stock;
- its starting date must match the plan;
- it must cover the complete ledger horizon.

The ledger consumes timeline events exactly. It does not inspect
`BuildingLevel.income`, calculate activation dates, or reconstruct income
replacement rules.

A temporary backward-compatible `income_timeline=None` mode retains the
previous no-income ledger behavior for callers pending higher-level
orchestration updates.

## Feasibility

Balances may become negative. Income is applied before expenses on the same
date. The first deficit remains the first expense entry after which any resource
component is negative, using canonical resource order for ties.

Later income does not erase the fact that an earlier deficit occurred.
