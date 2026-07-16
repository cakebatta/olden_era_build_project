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
- Every dwelling-linked `UnitFamily` contains one base-unit SID, two distinct upgraded-unit SIDs, positive weekly growth, and non-zero recruitment costs.
- Both upgraded-unit alternatives in each dwelling family have identical recruitment costs.
- Each recruitment dwelling has building levels 1 and 2.
- The city assets attach one shared `UnitFamily` to the dwelling definition.
- Certified baseline income effects identify a resource and level-specific amount.
- `BuildingLevel.income` retains that baseline amount as a normalized `ResourceCost` vector.
- The income amount does not establish cadence, activation delay, or construction-day production.

## Project-Owner Gameplay Assumptions

The following deterministic gameplay rules are canonical project assumptions
but are not independently encoded in the parsed assets.

### Building income timing

- A completed income building begins generating its retained income amount on the following day.
- It continues generating that amount daily while available.
- A building available in the effective starting state generates income on the plan starting date.
- For a multi-level building SID, only the highest active level generates income.
- When an upgrade completes, the lower level generates on the construction day and the upgraded amount replaces it on the following day; levels do not stack.

These timing assumptions are deliberately separate from the asset-derived
`BuildingLevel.income` amount.

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
- The two upgraded-unit alternatives share the same dwelling level.
- Any mixture of base and upgraded creatures may be recruited from available shared stock.
- Already recruited base units may be upgraded for the cost difference.
- Recruitment and upgrading may occur on the same day required construction completes.
- Recruitment is optional.

## Modelling Boundaries

- Resource pickups are random and excluded from modelling.
- Building-income cadence and activation belong to the Income Timeline domain, not the parser.
- The parser retains only authoritative income amounts.
- Recruitment stock, spending, upgrading, and income timing remain separate deterministic domains.
