# Building Income Parser Contract

`BuildingLevel.income` is immutable, authoritative data parsed from the
certified baseline `bonusesPerLevel` income effect in each city asset.

The value is a normalized `ResourceCost` amount vector. It does not encode:

- daily or weekly cadence;
- construction-day production;
- activation delay;
- optional effect selection;
- percentage or conditional modifiers.

A zero-valued `ResourceCost` means the building level has no certified baseline
income effect. Multiple supported resource entries and repeated entries are
normalized into one vector.

Only baseline `sideRes` effects in `bonusesPerLevel` are retained. Optional and
uncertified effects remain outside the canonical building model. Malformed
baseline effects raise `CityParseError` with source, building SID, and level
context.

Income components are required to be nonnegative at the `BuildingLevel`
boundary. `ResourceCost` remains signed because balances and comparison deltas
use negative values elsewhere.
