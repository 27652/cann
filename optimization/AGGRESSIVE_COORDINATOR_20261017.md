# Aggressive optimization round (2026-10-17)

User authorization: parallel research of the previously proposed structural
optimizations, followed by direct Fast Track evaluation of qualified candidates.

## Ownership and baseline

- Coordinator owns enrollment, formal POST, result attribution and promotion.
- Research workers own only their isolated `aggressive-*` candidate directories.
- CAModel remains host-lease serialized; compilation and host tests may overlap.
- Baseline discovered during startup: official submission
  `6ad2d3be193e507d8e0a014d`, Pass 15/15, score 14.37,
  `evidence/formal/fast-track-6ad2d3be/`. Offline validation passed.
- Root kernel at startup matches that bundle, SHA256
  `782b57322a4f2ce9c40182e303d77e413b843f58796ad86d2980e6794c8dbc56`.
- Earlier workers may use the immutable 14.34 bundle as their baseline; this
  is recorded per candidate and does not grant the candidate any official score.
- Other concurrent work exists, including `int8-*-k*` and `upper_bound/`.
  Do not overwrite it or adopt its outputs without identity verification.

## Parallel work units

| Directory | Hypothesis | Submission rule |
|---|---|---|
| `candidates/aggressive-int8-all-k/` | remove large-K FP32 conversion using safe INT32 partial sums | compile + targeted host checks; explicit device-unverified risks |
| `candidates/aggressive-n-split/` | expose N parallelism with complete row-max protocol | only if ownership/reduction protocol is complete |
| `candidates/aggressive-tile-streaming/` | consume bounded Cube row jobs earlier; reduce staging | preserve row-max and synchronization obligations |
| `candidates/aggressive-vector-quant/` | reduce scalar mask/exact-correction work | no-exact variant is diagnostic only, not a correctness candidate |
| `candidates/aggressive-workspace-launch/` | eliminate workspace for a safe shape-specialized path | no unsafe persistent buffer or premature free |

Host-only Fast Track enrollment must explicitly say that no local device
validation was completed. It must not manufacture INT32 mismatch fields.
The original strict-device enrollment remains independent and unchanged.

## Formal execution

Use a dedicated queue under `/tmp/opencode/aggressive-coordinator-20261017/`.
The existing host-wide formal lock still serializes it against other queues.
Before POST check other unresolved queues and active formal processes; never
use a new queue to evade an uncertain accepted submission.

Each project must contain the full recoverable template context and a built
binary whose hash matches qualification metadata. The CLI obtains the current
dynamic editable list and freezes its actual upload manifest before POST.
Authentication contents and raw replies stay out of the repository/dialogue.

Stop the affected formal flow on expired authentication, uncertain acceptance,
missing submission-bound score, or exhausted explicit 429 retries. Do not
repeat an unchanged accepted payload. A formal pass alone does not imply a
score improvement, broad correctness, or permission to overwrite a changing root.

Promotion requires strict improvement over the latest verified best, full
evidence/recovery, and an unchanged or conflict-free root. Each actual promotion
gets its own scoped Git commit under the updated AGENTS.md rule; unrelated
changes, including AGENTS.md itself, must not be staged.
