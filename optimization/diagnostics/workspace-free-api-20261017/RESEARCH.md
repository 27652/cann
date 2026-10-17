# Workspace-free Cube→UB feasibility audit

2026-10-17. Scope: installed CANN 9.1.0, target **dav-2201**, current root
matching official submission `6ad33b78193e507d8ea310c4` (15/15, score 19.45).
This is a source/API diagnostic, **not a numerical candidate or performance run**.
No root kernel, frozen `op/` file or formal bundle was modified.

## Decision

Do **not** implement the proposed direct Cube→VECIN path by merely changing
`CType`, NZ format or calling `GetTensorC(LocalTensor)`: on this target the
installed client stages the result through internal GM. Its LocalTensor
signature does not establish workspace-free transport. The initial hypothesis
was worth checking, but this specific implementation route is blocked by the
toolkit's target capability and transport implementation, not just by missing
NZ layout code or synchronization design.

This does not prove all workspace-reduction strategies impossible, nor rule out
undocumented hardware facilities. No unsupported intrinsic or architecture macro
override is proposed. In particular, using bounded GM tiles can remove the full
M×N allocation while retaining GM traffic; that is a distinct hypothesis, not
direct L0C→UB.

## Source evidence

Paths below are relative to `CANN/x86_64-linux/asc/`; exact installed paths and
SHA256 fingerprints are in `source-audit.json`.

1. `impl/adv_api/detail/matmul/utils/matmul_utils.h:26-38` selects
   `USE_SSBUF` for architecture 3510 (unless compatibility mode is requested),
   and `USE_WORKSPACE` for the other targets, including 2201.
2. `impl/adv_api/detail/matmul/feature_trait/matmul_chip_cap.h:67-109`
   maps 2201 to CHIP_TYPE_220; parsing the named fields and its table row yields
   **ifSupportL0CToUB=false**. `matmul_feature_trait.h:101-107` returns that
   capability. `capability.asc` compile-time asserts it on the actual target.
3. `include/adv_api/matmul/matmul_client.h:1262-1319` (non-SSBUF branch):
   synchronous `GetTensorC(LocalTensor)` calls `GetGlobalAddr<T,false>(c)`,
   sends that GM address, waits, and calls `CopyToUB` for UB C. The address
   helper at 1739-1752 calls `client->AllocUB` and returns a GM staging address.
   The allocator name must not be interpreted as direct physical UB access.
4. `impl/adv_api/detail/matmul/kfc/matmul_server_impl_c220.h:177-207`
   treats only L1 C as a LocalTensor; otherwise it creates a GlobalTensor from
   the received address and calls the GM `GetTensorC` overload.
5. The explicit GM+LocalTensor overload at client lines 1323-1351 writes GM and
   then invokes `CopyToUB`. `AsyncGetTensorC` at 1475-1497 requires
   `cacheWorkspaceAddr` and also copies from GM. `WaitGetTensorC` is an MTE2→V
   completion event, not a new Cube→UB transport.
6. `GetTensorCWithoutGm` at 1863-1887 is inside `#if defined(USE_SSBUF)`;
   its existence does not make it available on dav-2201. DualMaster remains
   incompatible with GetTensorC; combining them cannot resolve this restriction.
7. `impl/basic_api/dav_c220/kernel_operator_fixpipe_impl.h:407-445`
   implements the shown LocalTensor Fixpipe overload as **L0C→L1** (`__cbuf__`),
   and the GlobalTensor overload as L0C→GM. Passing VECIN to the former is not
   evidence of UB support and risks targeting the wrong memory space.

NZ restrictions in interface comments are insufficient evidence of a supported
direct path. Format eligibility and physical transport are separate questions.

## Correction to the TBest premise

`optimization/TBEST_ANALYSIS_20261017.md` is a historical comparison against
submission `6ad2cb6b193e507d8e02c24b`, not against the current 19.45 version.
Its 142.99× point-11 gap must not be attributed to current root performance.

Current submission's archived official times and its own `best_time` fields:

| Point | Current us | Recorded best us | Ratio |
|---:|---:|---:|---:|
| 1 | 18.41 | 2.06 | 8.94× |
| 2 | 9.36 | 1.67 | 5.60× |
| 3 | 12.36 | 2.11 | 5.86× |
| 4 | 20.75 | 7.55 | 2.75× |
| 5 | 17.66 | 8.28 | 2.13× |
| 6 | 38.90 | 12.02 | 3.24× |
| 7 | 61.65 | 14.68 | 4.20× |
| 8 | 136.64 | 15.80 | 8.65× |
| 9 | 103.41 | 19.27 | 5.37× |
| 10 | 266.85 | 35.63 | 7.49× |
| 11 | 327.58 | 52.73 | 6.21× |
| 12 | 661.18 | 64.52 | 10.25× |
| 13 | 873.24 | 76.73 | 11.38× |
| 14 | 1931.74 | 173.37 | 11.14× |
| 15 | 4600.98 | 340.89 | 13.50× |

Source: `evidence/formal/dual-aiv-fixed-6ad33b78/evidence.json`, archived score
query time `2026-10-17T09:10:55Z`. No live ranking query was made here. Full
testcase IDs are preserved in `source-audit.json`. These ratios are neither
stage measurements nor a score formula; shape mapping is unknown. They provide
no basis for claiming workspace/synchronization accounts for 90% of runtime,
or for claiming that a particular rewrite will yield 10×.

## Completed checks and reproduction

- Read-only source audit passes; parses the feature table, checks the relevant
  transport statements, verifies root SHA256 against the official manifest and
  records input fingerprints.
- Three lightweight unit tests pass: real source/baseline parsing, rejection
  of a mocked transport change, and rejection of a mocked capability change.
- `python3 evidence/formal_evidence.py validate evidence/formal/dual-aiv-fixed-6ad33b78`
  returns `valid=true`, score 19.45. This is offline consistency validation,
  not a fresh service result.
- Compile-only ASC object succeeds with CANN 9.1/dav-2201, checking both
  `USE_WORKSPACE` and the negative L0C→UB capability. See `compile.log`.
  Initial configuration attempts lacked the correct package path/environment;
  first compilation also used an incorrect `AscendC::CFG_NORM` namespace.
  After sourcing `set_env.sh` and correcting it to `CFG_NORM`, compilation passed.
- **No device correctness test, CAModel timing, upper-bound timing, new formal
  submission or new score.** The probe does not implement the operator and
  must not be submitted. Its compiler warning is an intentional audit message.

```bash
python3 optimization/diagnostics/workspace-free-api-20261017/audit.py \
  --toolkit /mnt/data_server/llm_course/zzfs_202615/Ascend/cann-9.1.0
AUDIT_TOOLKIT=/mnt/data_server/llm_course/zzfs_202615/Ascend/cann-9.1.0 \
  python3 -m unittest discover \
  -s optimization/diagnostics/workspace-free-api-20261017 -p 'test_audit.py' -v
source /mnt/data_server/llm_course/zzfs_202615/Ascend/cann-9.1.0/set_env.sh
cmake -S optimization/diagnostics/workspace-free-api-20261017 \
  -B optimization/diagnostics/workspace-free-api-20261017/build \
  -DASC_DIR="$ASCEND_HOME_PATH/lib64/cmake"
cmake --build optimization/diagnostics/workspace-free-api-20261017/build -j2
```

The probe deliberately references the installed internal capability trait for
diagnosis only; it is not a portable production API dependency.

## Next useful experiment

Prefer a single-launch, bounded **GM** tile/row buffer with full-row activation
resident in UB for N≤4096, or matched Cube/epilogue/synchronization ablations,
rather than mislabeling the client LocalTensor path as workspace-free. Preserve
Cube parallelism and establish ownership/backpressure and memory visibility
before combining it with other changes. A smaller allocation alone does not
remove GM traffic or prove lower runtime; existing FIFO feedback should inform
the design. Removing host synchronization also requires a proven buffer
lifetime, and its contribution to the official timing remains unknown.

During a score freeze, any new accepted submission's per-testcase official
times may be compared to this baseline by exact testcase ID, with absolute and
relative changes and query provenance. That is temporary feedback only: no
automatic promotion without an attributable, strictly higher official score.
