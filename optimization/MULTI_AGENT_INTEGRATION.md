# Three-Agent integration — 2026-10-16

## Completed matched measurements — 2026-10-17

All six pair tasks reached `passed`, return code 0, through the shared queue.
Coordinator's `compare_scheduled_pair.py` accepted source/binary identity,
common input/golden/script/environment fingerprints and strict INT32 checks.
Both sides of every pair have zero INT8 mismatches, accepted scale, and passing
FP32 diagnostics. These are local single-case diagnostics, not official scores.

| Candidate | Case | Baseline task_cycles | Candidate task_cycles | Change | Baseline / candidate total_ticks |
|---|---|---:|---:|---:|---:|
| quant | `1x1144x1 / half_boundary` | 207223 | 117037 | -43.521% | 207581 / 117374 |
| shape | Case12 `1024x256x64 / random` | 3369038 | 3370081 | +0.031% | 3369512 / 3370450 |
| cache | `2x4097x32 / random` | 819869 | 815554 | -0.526% | 820296 / 816010 |

Pair task IDs, source/binary hashes and full fingerprints are preserved under
`/tmp/opencode/multi-agent-integration-5574de4/{quant,shape,cache}-pair-validated.json`
and the queue's immutable snapshots/results. Cache compares identical revised
source with `QUANT_CACHE_TWO_TILES=0/1`; it does not isolate resident-tail versus
the old cache-enabled implementation. ASC discovery was repaired by sourcing
the validated CANN environment, without overwriting other worktrees' binaries.

The original three submissions scored 7.26 (quant), 7.27 (shape), and 7.26
(cache), below the original verified 11.67 baseline; none was promoted.
Later independent research has newer formal results; consult `report.md` rather
than interpreting this historical integration baseline as the current best.
At final queue inspection no tasks remained queued/running and no model or
Coordinator process remained; no empty Worker was restarted.

## Pinned baseline

- Git HEAD shared by all research worktrees:
  `5574de4f5a378ae661bf1c7647a7fc36e2b3a541`.
- `AGENTS.md` SHA256:
  `753d94efa0be840f31039e74176b088033592d952a22a36d89b25d7c246bda1f`.
- Queue: `/tmp/opencode/multi-agent-integration-5574de4/queue`.
- All Agent submissions must explicitly use that absolute queue path. Defaults
  and environment inheritance are not the integration contract.

| Agent | Worktree | Candidate directory | Research objective |
|---|---|---|---|
| quant | `/tmp/opencode/worktrees/research-quant` | `optimization/candidates/agent-quant` | Reduce exact quantization overhead without weakening correctness |
| cache | `/tmp/opencode/worktrees/research-cache` | `optimization/candidates/agent-cache` | Reduce activation reloads / UB movement |
| shape | `/tmp/opencode/worktrees/research-shape` | `optimization/candidates/agent-shape` | Shape-specific dispatch / tiling |

Each Agent must read its own `AGENTS.md`, verify HEAD/hash, and report the
acknowledgement. Presence and hash equality alone are not proof that an Agent
loaded the rules. Each Agent records work in its candidate `RESEARCH.md`.

## Queue integration evidence

Coordinator submitted one host-only task from each worktree, then consumed all
three through the same Scheduler/host lease. No simulator was invoked.

| Agent | Task ID | Priority | Observed result |
|---|---|---:|---|
| quant | `1792193939303-edfd837a1e` | 10 | passed, returncode 0 |
| cache | `1792193939384-81950023f8` | 5 | passed, returncode 0 |
| shape | `1792193939493-3d4b1d49ef` | 1 | passed, returncode 0 |

Task snapshots, `task.json`, and `run.log` are beneath the shared queue root.
These are integration checks, not performance or formal correctness evidence.

## Research handoff and first real smoke

All three Agents acknowledged the pinned HEAD and AGENTS.md hash in their
handoffs. Candidate sources and research records remain isolated in the
worktrees above; no root kernel was replaced.

| Agent | Candidate source SHA256 | Completed validation | Device status |
|---|---|---|---|
| quant | `cc7784d4546e15f879ac12583d6ef3bca058aa36bf8697f657a482e1a0d87bc4` | Agent reports 68,108,865 unit-scale, 3,979,947 exact-quantization and 2,000,000 mask-boundary host checks | Compiled; unified Worker smoke passed |
| cache | `243cc82f07bf6e846a2dcdcffe56d5a02b26fc4346302e7bf6856721ebd3be22` | Agent reports 40 host residency/traversal checks | ASC CMake discovery failed in Agent shell; no binary or queued smoke |
| shape | `a7762ac6ad96a29edaf96ebbe649b85b9a38e3cd2cea75db07592eedb1a9695f` | Agent reports 401,457 host dispatch combinations, 6 golden self-tests and 9 scheduler tests | No binary or queued smoke |

Coordinator directly inspected quant task `1792194253045-b3e8150ba5`:

- Queue terminal status: `passed`, return code 0; unified Worker log confirms it.
- Case: `1x1144x1`, `half_boundary`; CANN 9.1.0 / Ascend910B1.
- Binary SHA256: `3a26a5dd3a1ea85912a0fd020eb6a2ed3e62db8151b8684f5b74d88a667525f0`.
- Strict INT32 golden: 0 INT8 mismatches; scale accepted, maximum difference 0.
- FP32 diagnostic: 0 INT8 mismatches; scale accepted, maximum difference 0.
- CAModel diagnostics: `task_cycles=117037`, `total_ticks=117441`.
  No matched baseline measurement was obtained; these do not establish speedup.
- Evidence: queue-relative
  `results/agent-quant-unit-output-scale-smoke/benchmark/1x1144x1_half_boundary/optimized/result.json`,
  `run.log`, and `snapshots/1792194253045-b3e8150ba5/`.
- Result-directory `task.json` is the launch-time snapshot and still says
  `running`; terminal scheduling status is in the queue, not that snapshot.

This establishes one real candidate's path through the unified Worker, not
real-simulator priority-preemption acceptance or broad device correctness.
No new official submission/score was obtained and no candidate was promoted.

## Ownership and execution

- Research Agents edit only their own worktree and candidate/build directories.
- They enqueue single-case smoke tasks; they do not run CAModel or Workers.
- Coordinator is the only queue consumer. `multi_agent_worker.py` is a bounded
  driver of the existing Scheduler, not a replacement resource implementation.
  It releases/reacquires the canonical host lease at every case boundary and
  honors explicit pause requests. Automatic priority yields allow the next
  claim to select the higher-priority task.
- Coordinator alone handles official submissions and promotion under AGENTS.md:
  exact recoverable payload, official 15/15, submission-bound comparable score,
  and strict improvement over the verified historical score of 11.67.
- No candidate currently inherits that score. Integration itself does not
  promote a candidate or establish simulator performance.

## Fast Track default

- All future research Agents should enroll every candidate that satisfies the
  strict INT32 and build-identity contract in `optimization/fast_track.py`;
  enrollment is the default handoff to formal evaluation, not an optional
  manual selection step.
- The Fast Track Coordinator worker is the sole process allowed to invoke the
  CANNJudge client. It serially drains qualified snapshots after terminal result
  reconciliation, and halts on unresolved outcomes. It never reads or copies credentials.
- Formal 15/15, same-submission score provenance, and strict improvement over
  the verified historical best remain required for promotion. A submitted
  candidate is not automatically promoted.
- Operational details and the metadata contract are in `optimization/FAST_TRACK.md`.
- Fast Track is enabled as the default Agent handoff. Agent dispatch must call
  `fast_track.py enroll` after the candidate contract passes; the Coordinator
  runs the serialized `worker` and uses `reconcile` for pending/uncertain
  submissions. It never retries an unresolved POST. See
  `optimization/FAST_TRACK.md` for the exact commands.
