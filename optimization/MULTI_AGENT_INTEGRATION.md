# Three-Agent integration — 2026-10-16

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
