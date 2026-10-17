# Single-launch N-shard partial-max candidate (D)

## Hypothesis

For tiny M and wide N, complete-row Vector ownership leaves AIV parallelism
unused. This candidate assigns each row's N interval to an AIV shard, stores
one aligned partial maximum per row/shard, synchronizes inside the MIX kernel,
and then lets the row owner quantize using the final row maximum.

## Validation

- Built with CANN 9.1.0 / Ascend910B1 / dav-2201.
- Initial simulator case `2x8192x65` failed strictly with 3686 INT8
  mismatches and non-matching yScale. The first implementation used scalar GM
  publication; it was changed to aligned DMA slots, but the corrected version
  has not yet completed a rerun because the shared CAModel lease was busy.
- No formal submission has been made.

## Risks

The protocol relies on multiple `SyncAll<false>()` phases in one MIX launch.
The implementation must prove that AIC and AIV participants reach identical
barriers and that partial maxima are visible before reduction. Until a clean
strict simulator result is obtained, this candidate is rejected for formal
submission. The existing complete-N path remains the safe fallback outside the
experimental dispatch condition.
