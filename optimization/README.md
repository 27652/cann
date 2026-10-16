# CAModel optimization and regression

## Latest snapshot

`op/kernel_v3.asc` is a frozen historical snapshot, not the current root. The current
root is `../kernel.asc`; its default `QUANT_MASK_FAST_PATH=0` differs from v3, and
its `K >= 65536` path uses FP32 Matmul. The external v3 evaluation and its limitations
are recorded in `../ev/V3_EVALUATION.md`. Measurements below describe earlier
versions unless explicitly stated otherwise.

## Fixed public test points

`test_points.json` lists 15 newly constructed regression cases (not the user's
15 hidden evaluation cases). The runner uses fixed per-case seeds, preserves
input binaries and NumPy golden binaries, and reports exact INT8 errors, scale
errors, binary hash and CAModel cycles. Newly added cases are not yet validated.

```bash
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py --suite --variants prior optimized
# Run a subset first; cases 12-15 may be expensive in CAModel.
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py --case-ids 1 2 3 4 5 6 --variants prior optimized
```

Target: CANN 9.1.0, Ascend910B1 (`dav-2201`). The original source is preserved
as `baseline/kernel.asc`. Production entry points and build files are unchanged.

## Changes

* Incorporate the supplied `op/kernel.asc` design: 4096-lane UB tiles and
  reciprocal-multiply hints (with Div fallback for tiny scales).
* For `N <= 4096`, reuse the activated FP32 row already resident in UB after
  `FindRowMax`. `ReduceMax` uses separate work/output buffers and does not modify
  this row. This eliminates the second GM read, INT32 conversion, two scaling
  operations and ReLU. Wider rows retain the existing two-pass path.
* Avoid reading approximate quotients and decoding floating-point fields for
  ReLU zeros.
* Only scalar-quantize valid output elements, not alignment padding. Padding
  lanes are independent during narrowing casts and are never copied to GM.
* Hoist output-scale FP32 normalization out of the per-element exact quantizer;
  the denominator is invariant for a row. This preserves the exact integer
  correction while removing repeated denominator decode/normalization work.
* Convert approximate FP32 quotients to floor-INT16 hints with vector `Cast`,
  instead of decoding each quotient's FP32 exponent/mantissa on the scalar
  pipe. Any bad/saturated hint is still repaired by the exact correction.
  The original scalar hint path is retained for `N <= 16`, where vector setup
  costs more than it saves.

The exact positive-element quantizer, rounding rules, dequant multiplication order,
large-K FP32 path, workspace layout and core partition policy are unchanged.
The approximate hint may differ, but its integer certification/correction is
unchanged. `op/kernel.asc` itself is not modified.

## Reproduce

```bash
source ../env.sh Ascend910B1
cmake -S optimization -B optimization/build
cmake --build optimization/build -j4
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py --variants baseline prior optimized
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py --shapes 4x17x32 --mode zero
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py --shapes 4x17x32 --mode mixed
```

Run these serially. Each run has its own input, output, model logs and
`result.json` under `results/<shape>_<mode>/<variant>/`. The driver checks INT8
output with exact equality and scales with `rtol=atol=1e-4`. It also propagates
runtime failures. `--resume` reuses an existing result only when its recorded
`binary_sha256` matches the current binary. It does not verify input/golden hashes,
benchmark-script hash, CANN/CAModel version, or source hash; use it only after
independently confirming those conditions.

Compare `task_cycles` from CAModel `profile_task_log0.toml`, not wall-clock
runtime (which is dominated by simulator startup/logging). `total_ticks` also
includes scheduling/model activity. Results are simulator measurements, not
physical-device latency. Absolute cycle counts depend on input data because
the original exact quantizer uses data-dependent scalar branches.

## Multi-agent CAModel scheduler

Agents may analyze, edit candidates, run host tests, and compile in separate Git
worktrees. CAModel is different: `optimization/camodel_scheduler.py` admits one
model process at a time using the host-wide `/tmp/opencode/camodel-host.lock`.
Queue state and immutable candidate snapshots live outside the repository by
default, and every task has its own result directory. The scheduler refuses
`optimization/results/`, duplicate tasks, unbound command files, tampered
snapshots, and incomplete experiment identity metadata. Commands execute from
the submitted snapshot, so later worktree edits cannot change a queued task.

Treat each case as one submitted command. `submit --priority N` sets the case
priority (default `0`); larger values run first and equal priorities remain
FIFO. Use `--cases-json` to enqueue a list of explicit per-case commands,
metadata, and optional priorities under separate result directories. When a
higher-priority case arrives during a lower-priority case, the scheduler sets
`yield_requested`; the simulator finishes normally, the Worker releases the
host lease and exits its loop with `yielded=true`, and unclaimed cases remain
queued. `pause TASK_ID` requests the same case-boundary yield. Neither action
sends a signal to the simulator. The existing timeout path remains the only
case-runner termination mechanism.

Submit is non-blocking from the agent's perspective:

```bash
python3 optimization/camodel_scheduler.py submit \
  --cwd "$WORKTREE" \
  --result-dir "/tmp/opencode/camodel-results/$TASK_ID" \
  --bind "$WORKTREE/kernel.asc" \
  --bind "$WORKTREE/optimization/build/bench_optimized" \
  --bind "$WORKTREE/optimization/benchmark.py" \
  --bind "$WORKTREE/optimization/int32_golden.py" \
  --bind "$WORKTREE/optimization/test_points.json" \
  --metadata /tmp/opencode/task-metadata.json \
  --priority 10 \
  -- python3 optimization/benchmark.py --case-ids 1 --variants optimized
python3 optimization/camodel_scheduler.py worker --loop
python3 optimization/camodel_scheduler.py list
```

For case-level scheduling, provide `--cases-json /tmp/opencode/cases.json`
instead of the trailing command. It must contain an array like:

```json
[
  {"command": ["python3", "optimization/benchmark.py", "--case-ids", "1", "--variants", "optimized"],
   "metadata": {"case": 1}, "priority": 10},
  {"command": ["python3", "optimization/benchmark.py", "--case-ids", "5", "--variants", "optimized"],
   "metadata": {"case": 5}, "priority": 0}
]
```

Metadata must contain `candidate_id`, `source_sha256`, `binary_sha256`,
`case`, `variant`, `golden_mode`, and `environment_fingerprint`. The worker
records `queued`, `running`, `passed`, `failed`, `timeout`, or `cancelled` and
writes `task.json` and `run.log` beneath the task result directory. The lease
file descriptor is passed to the benchmark child, so the host lock remains held
until the model process exits. Existing unmanaged model/benchmark processes are
detected and cause fail-closed requeue; they are never killed.

The scheduler does not perform formal submissions or update `report.md`; a
coordinator reviews completed results and applies the existing formal score and
promotion rules. Do not use the current shared `optimization/build` from two
worktrees for writes; use a worktree-local build directory or an independent
out-of-tree build.

Create an isolated research worktree from the repository root (do not place
two agents in the same writable directory):

```bash
git worktree add /tmp/opencode/worktrees/vector -b research/vector
git worktree add /tmp/opencode/worktrees/cache -b research/cache
cmake -S /tmp/opencode/worktrees/vector/optimization \
      -B /tmp/opencode/worktrees/vector/optimization/build
cmake --build /tmp/opencode/worktrees/vector/optimization/build -j4
```

The coordinator should review completed queue records and update the main
worktree's `report.md`; agents should not edit another worktree or reuse its
build/result directories.

### Real acceptance (single CAModel only)

After confirming no unrelated model process is active, the coordinator can run
the opt-in acceptance script with an existing binary:

```bash
python3 optimization/accept_scheduler.py --real-camodel \
  --toolkit /mnt/data_server/llm_course/zzfs_202615/Ascend/cann-9.1.0
```

It uses only Case 1, creates a fresh `/tmp/opencode/scheduler-acceptance-*`
directory, and exercises one Worker, two competing Workers, enqueue-while-
running, staging-worktree mutation after enqueue, and termination of only the
acceptance Worker. It must not be used while another user's model is running.
The resulting `acceptance.json` is local scheduler evidence, not an official
score or formal CANNJudge result.

## Initial measurements (before incorporating `op/kernel.asc`)

The repository's original case (`M=16,N=16,K=32`) passed before and after the
first optimization: task duration 96,298 -> 91,149 cycles, total ticks
97,066 -> 91,630. Both INT8 and FP32 outputs were bit-identical to the supplied
golden. These measurements preceded the additional padding-lane optimization.

Attempting four-row Cube ownership partitions was rejected by the tiling API;
that experiment is **not** part of the final kernel. No approximate division
shortcut or relaxed output tolerance was introduced.

This is a targeted optimization, not a claim of a global optimum. The scalar
exact quantizer remains a significant cost; replacing it safely with vector
integer logic would require additional rounding/subnormal boundary validation.

Host-side helper validation:

```bash
python3 optimization/check_quant.py
```

This checks arbitrary hints against the exact FP32 division reference helper
and checks values around half-integer rounding thresholds. It does not replace
CAModel validation of pipeline synchronization and vector instruction behavior.

## Comparison against supplied prior optimization

Measured vector-hint candidate, before the final `N <= 16` specialization:

| M,N,K | Mode | Prior task cycles | Candidate task cycles | Change |
|---|---|---:|---:|---:|
| 16,16,32 | random | 69,661 | 70,560 | 1.29% slower |
| 17,33,65 | random | 104,042 | 101,470 | 2.47% faster |
| 2,1025,32 | random | 234,914 | 232,342 | 1.09% faster |

All three had zero INT8 mismatches and zero scale difference against NumPy.
These are single measurements, not statistical confidence intervals. The final
small-N specialization is recorded separately in `benchmark_final.log`.
The user's 15-case evaluation shapes are unavailable; these results do not
establish improvement on that evaluation suite. In particular, this incremental
work does not eliminate the scalar correction bottleneck or explain away the
large gap to the user's reported best implementations.

Final small-N-specialized build (all outputs match exactly, including scales):

| M,N,K | Mode | Prior task cycles | Final task cycles | Change |
|---|---|---:|---:|---:|
| 16,16,32 | random | 69,661 | 72,238 | 3.70% slower |
| 4,8,16 | random | 32,753 | 32,767 | 0.04% slower |
| 17,33,65 | random | 104,042 | 100,591 | 3.32% faster |
| 4,17,32 | mixed | 31,879 | 32,750 | 2.73% slower |

The small-N specialization did **not** recover the small-shape regression.
The current root kernel is an experimental candidate, not a consistently
faster replacement for `op/kernel.asc`. Prefer the untouched `op` version if
requiring the previously established 15-case correctness/performance baseline.
