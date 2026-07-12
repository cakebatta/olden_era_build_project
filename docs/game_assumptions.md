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

## Verified Rules

- One building may be constructed per day.
- Upgrade branches have identical recruitment costs.
- Buildings form a directed acyclic dependency graph.
- Multiple valid topological build orders may exist.
- Resource pickups are random and are intentionally excluded from modelling.
- Localization never replaces internal SIDs.

The planner should optimize for efficient and adaptable build paths rather than predicting map economy.
