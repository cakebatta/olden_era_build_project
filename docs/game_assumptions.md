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

## Project-Owner Gameplay Assumptions

The following deterministic gameplay rules were supplied by the Project Owner. They are canonical project assumptions but are not independently encoded in the currently parsed city and unit assets:

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

## Modelling Boundaries

- Resource pickups are random and are intentionally excluded from modelling.
- The planner should optimize for efficient and adaptable build paths rather than predicting map economy.
- Recruitment stock progression, recruitment spending, and unit upgrading should remain deterministic and should consume the verified `UnitFamily` data without reinterpreting raw asset layout.
