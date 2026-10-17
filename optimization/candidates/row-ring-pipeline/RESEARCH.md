# Row-ring Cube/Vector pipeline candidate

## Hypothesis

The current 16.07 implementation computes a complete `M x N` INT32 plane and
then globally synchronizes before VectorStage. This candidate uses the
`cann-ops-adv` `GMMQuantMixCore` pattern: each paired AIC/AIV owns a fixed
16-row job and two GM INT32 slots. AIC computes the next job while AIV
quantizes the previous slot. AIV acknowledges completion before the slot is
reused. The candidate remains one MIX launch and keeps complete-N ownership,
so row-max has no cross-core reduction.

## Status

- Isolated from the current root; root and frozen `op/` files are untouched.
- CANN 9.1.0 / `dav-2201` formal-template and benchmark builds pass.
- Initial CAModel smoke (`64x513x65`, `65x257x33`, `1025x65x33`) completed
  with strict INT32 golden: all three had zero INT8 mismatches and exact
  recorded yScale values. This validates the original slot protocol on
  multiple jobs, N tails, and slot reuse, but does not validate the later
  explicit cross-core/N-tile source revision; that revision is being rebuilt
  and rerun separately.
- Candidate source SHA256: `0ce41f1d47b2844b5d69108c5f3745a1087c844ff8af3c264b008276cb20efa1`.
- CLI submission `6ad31d99193e507d8e6c5620` completed `Pass`, 15/15, all
  `precision_ratio=1`; the ranking result is bound to the same submission ID,
  rank 212, official score **15.71**. Recoverable formal bundle:
  `evidence/formal/row-ring-pipeline-6ad31d99/`; local protected raw responses
  are `/tmp/opencode/row-ring-pipeline-submit.json` and
  `/tmp/opencode/row-ring-pipeline-submit.ranking.json`.
- This is below the verified 16.66 best (`6ad31941193e507d8e654e7b`), so it
  is not promoted. CAModel timings are diagnostics only and do not substitute
  for the official score. The later cross-core/N-tile revision passed three
  strict INT32 smoke shapes and four representative benchmark shapes, but that
  is not a full local regression; residual event-ordering, tail and K-chunk
  risks remain.

## Risks

The event IDs use the documented AIC/AIV cross-core event range observed in
the installed CANN headers, but this specific paired ring protocol is not yet
device-proven beyond the first smoke revision. It assumes `PIPE_FIX` producer
notifications and `PIPE_MTE2` consumer acknowledgements provide the required
ordering. Tail rows, multiple row jobs per block, K-chunk atomic accumulation,
and scale residency still require strict INT32 validation. If a case hangs or
produces incorrect output, the candidate is rejected rather than weakening
the golden comparison.

## Public reference

`https://gitee.com/ascend/cann-ops-adv/raw/master/src/transformer/grouped_matmul/grouped_matmul_quant_mixcore.h`

The public operator has different output semantics (BF16/FP16 dequant and
activation); only its block/ring/event organization is borrowed.
