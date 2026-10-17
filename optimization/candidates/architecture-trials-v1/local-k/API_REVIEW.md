# L0C API review — 2026-10-17

Scope: installed CANN 9.1 headers only. This is not proof of server CANN or
device numerical behavior, and no local-k submission was performed here.

## Findings

- `asc/impl/adv_api/detail/matmul/matmul_impl_base.h:560-565,598-603`:
  GM `SetTensorA/B` updates the input then calls `Scheduler->Reset()`.
- `scheduler/base/scheduler_norm_base.h:64`: normal scheduler Reset only
  sets `isFirstIter_ = true`; it does **not by itself prove L0C is freed**.
- `scheduler/base/scheduler_norm.h:119-134`: ScheduleOnce allocates the
  CubeOutBuffer only for `!enPartialSum`, then computes with enPartialSum.
  This is evidence consistent with reuse on that policy, not a guarantee that
  the actual selected policy, SetSingleShape changes, and GetTensorC lifetime
  all satisfy the proposed external-chunk protocol.

## Decision

The earlier inference “scheduler Reset implies accumulator loss” is not
established. Conversely, compilation does not prove safe accumulator reuse.
Keep the original `local-k` external-chunk Iterate/GetTensorC prototype out of
formal submission until the chosen policy and output lifetime are traced and
a strict multi-chunk device case is run.

The distinct `local-k-safe` source avoids this external-chunk protocol for
K below 131072 by computing it in one Matmul call, with the original safe
chunk fallback at larger K. Its independent 15/15, score 16.69 evidence at
`evidence/formal/local-k-safe-6ad3338a/` is therefore **not proof** of the
original local-k L0C-retention hypothesis. Do not merge it into the FIFO
candidate or resubmit the same payload.
