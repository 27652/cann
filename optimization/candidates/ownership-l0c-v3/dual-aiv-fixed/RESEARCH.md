# Correct logical AIV ownership: official 19.45

2026-10-17. Parent architecture is tile16 persistent 16.66 (not FIFO).
Use MIX_AIC_1_2 and partition rows over logical GetBlockIdx directly;
installed dav_c220 implementation already includes the sub-block number.
Old dual-aiv incorrectly multiplied this logical ID again, causing skipped rows.
No numerical expressions, exact repair, Cube tile order or workspace changed.

Verification: benchmark compiles CANN 9.1/dav-2201; 320 host ownership models
pass; strict INT32 CAModel at 17x513x65, 2x33x129, 65x257x33 passes with zero
INT8 mismatches and exact yScale. Inputs include zero rows, negative scales,
and M/N/K tails. Logs/fingerprints are in results/strict-v1; those generated
logs are not necessary to restore the official submission.

Official submission 6ad33b78193e507d8ea310c4: Pass 15/15, all precision_ratio=1,
exact-ID ranking score 19.45. Real raw service files are protected under
/tmp/opencode/ownership-l0c-v3-dual-result*.json. Actual editable payload is
kernel.asc only; full eight-file context is recovered under
evidence/formal/dual-aiv-fixed-6ad33b78/source. Manifest is archived alongside.
Source hash bae4d14b3b7eaa918034a8f0bde94bfa49ce38dc2c992d9e7d7326c50ac9fc95.
Evidence validates and decide versus FIFO 16.89 is eligible.

Promoted root after confirming it was clean and matched FIFO. Former root
remains recoverable from evidence/formal/tile-fifo-6ad335a8/source/kernel.asc.
No FIFO/UB/L0C combination was submitted. Remaining risks include hardware
sync semantics across versions, general FTZ/subnormal and large-K boundaries;
official tests and three targeted cases do not prove all legal inputs.
