# Game Assumptions

## Tournament Assumptions

Starting resources:

- 10000 Gold
- 10 Wood
- 10 Ore
- 5 Gemstones
- 5 Crystals
- 5 Mercury
- 50 Alchemical Dust

## Verified Asset Facts

These rules are directly supported by the canonical parsed assets:

- One building may be constructed per day.
- Buildings form a directed acyclic dependency graph.
- Multiple valid topological build orders may exist.
- Localization never replaces internal SIDs.
- Every supported playable faction has one dwelling-linked `UnitFamily` for each tier from 1 through 7.
- Every dwelling-linked `UnitFamily` contains:
  - one base-unit SID;
  - two distinct upgraded-unit SIDs;
  - a positive base weekly-growth value;
  - a non-zero base recruitment cost;
  - a non-zero upgraded recruitment cost.
- Both upgraded-unit alternatives in each dwelling family have identical recruitment costs.
- Each recruitment dwelling has building levels 1 and 2.
- The city assets attach one shared `UnitFamily` to the dwelling definition rather than separately encoding recruitment access by dwelling level.
- The assets do not independently specify whether level 1 permits only base recruitment or whether level 2 unlocks upgraded recruitment.

### Town-building income data

The canonical city assets encode town-building resource production through
`sideRes` bonus entries.

- A `sideRes` entry identifies the produced resource and amount.
- Baseline building effects appear in `bonusesPerLevel`.
- Selectable or optional building effects may also contain `sideRes` entries in
  `optionalEffectsPerLevel`; these must not be silently treated as guaranteed
  baseline income.
- Building upgrades may change the amount produced by providing a different
  `sideRes` value for each building level.
- The raw bonus entries do not explicitly encode a daily or weekly frequency.
- The raw bonus entries do not explicitly encode whether production occurs on
  the construction-completion day.
- The raw bonus entries do not explicitly encode delayed activation,
  accumulation, or external production modifiers.
- The current `BuildingLevel` parsed model does not retain `bonusesPerLevel`,
  `optionalEffectsPerLevel`, or normalized income data. Therefore current parser
  coverage is insufficient for deterministic town-income gameplay without a
  future, separately authorized parser/model extension.

The focused income-data validation script inventories all baseline and optional
`sideRes` entries by faction, building SID, level, resource, and amount. Its
runtime output is the canonical completeness report for the currently included
game assets.

## Project-Owner Gameplay Assumptions

The following deterministic gameplay rules were supplied by the Project Owner.
They are canonical project assumptions but are not independently encoded in the
currently parsed city and unit assets.

### Initial stock

- Initial stock equals one base-growth quantity.
- Initial stock ignores wall modifiers.

### Weekly stock

- Weekly stock is granted at the start of a week only to dwellings built before that week.
- A dwelling built on the first day of a week receives no weekly addition that day.
- Wall modifiers apply only to weekly additions.
- No wall or tier-1 wall: 100% weekly growth.
- Tier-2 wall: 150% weekly growth.
- Tier-3 wall: 200% weekly growth.
- Fractional growth rounds down.
- Unrecruited stock accumulates indefinitely.

### Recruitment and upgrades

- Base and upgraded recruitment consume one shared dwelling stock.
- Dwelling level 2 unlocks upgraded recruitment.
- The two upgraded-unit alternatives share the same dwelling level and do not require separate buildings.
- Any mixture of base and upgraded creatures may be recruited from available shared stock.
- Already recruited base units may be upgraded for the difference between the upgraded and base unit costs.
- Recruitment and upgrading may occur on the same day that required construction completes.
- Recruitment is optional.

### Town-building income timing

- Town-building income begins on the day after construction completes.
- A building completed on day 111 produces no income on day 111 and begins
  producing on day 112.
- Unless a future asset audit finds explicit frequency metadata elsewhere,
  production frequency and other income-timing behavior remain project-level
  gameplay assumptions rather than parser-derived facts.

## Modelling Boundaries

- Resource pickups are random and are intentionally excluded from modelling.
- The planner should optimize for efficient and adaptable build paths rather than predicting map economy.
- Recruitment stock progression, recruitment spending, and unit upgrading should remain deterministic and should consume the verified `UnitFamily` data without reinterpreting raw asset layout.
- Income gameplay must not infer optional `sideRes` choices as mandatory income.
- A future parser extension should translate raw income definitions into an
  explicit backend data structure; the Resource Ledger should not inspect raw
  JSON asset layout directly.
