# Fast Track

Fast Track is the default formal-evaluation handoff for research candidates.
The enrollment queue is enabled for all new Agent handoffs. It does not equate
local correctness with an official result and it does not auto-promote a score.

## Serial submission queue

The coordinator drains qualified jobs serially and enforces a 180-second
cooldown between POST submissions. The cooldown is persisted at
`/tmp/opencode/fast-track/submission-cooldown.json`, so a worker restart does
not reset the interval. `serve` sleeps until the remaining cooldown expires and
then immediately claims the next queued candidate. A submission that has an
unknown acceptance state still halts the queue and must be reconciled by
submission ID; the interval does not authorize blind resubmission.

## Candidate contract

An Agent must provide:

1. An isolated project/worktree snapshot.
2. Exactly one validation record: either a strict INT32 benchmark `result.json`
   (`int32_mismatches == 0`, `int32_scale_ok == true`) or the explicit
   `--host-validation` protocol below. Host-only qualification is not strict
   correctness evidence and does not assert that device validation passed.
3. A built candidate binary path and its 64-character SHA256.
4. A candidate ID and build/environment identity metadata.

Enrollment copies the eight known project source files, binary and selected
validation record to a queue snapshot. Source files are read-only and hashes
are checked again before execution.
It rejects duplicate project/candidate IDs, failed strict results and unsupported
top-level metadata. Only explicitly listed project files are copied; build caches
and credential-path names are excluded. Supply only reviewed source and metadata;
arbitrary embedded secrets are not automatically detected.

## Enroll

```bash
python3 optimization/fast_track.py \
  --root /tmp/opencode/fast-track/queue enroll \
  --project /tmp/opencode/worktrees/research-quant \
  --strict-result /tmp/opencode/results/quant/result.json \
  --candidate-id agent-quant-20261017 \
  --metadata /tmp/opencode/quant-fast-track-metadata.json
```

For a candidate with successful compilation and targeted host checks, but no
local device test, strict INT32 may be omitted in favor of this record:

```bash
python3 optimization/fast_track.py \
  --root /tmp/opencode/fast-track/queue enroll \
  --project /tmp/opencode/worktrees/research-quant \
  --host-validation /tmp/opencode/results/quant/host-validation.json \
  --candidate-id agent-quant-host-20261017 \
  --metadata /tmp/opencode/quant-fast-track-metadata.json
```

The JSON schema is versioned and identity-bound:

```json
{
  "schema_version": 1,
  "type": "host-only",
  "passed": true,
  "checks": ["compile", "targeted-host-check"],
  "fingerprint": {
    "source_sha256": "<kernel.asc SHA256>",
    "binary_sha256": "<compiled binary SHA256>",
    "environment": {"compiler": "<recorded compiler/toolchain identity>"}
  }
}
```

`checks` must be a nonempty array; `passed` must be JSON true. Its
source/binary/environment fingerprint must match the enrolled project, binary
and build. `risks` must explicitly contain `未完成本地设备验证` and describe
relevant unverified numeric, synchronization and UB risks. The queue snapshot
stores `host-validation.json`, records `validation_mode: host-only`, and
checks its hash before any submit attempt, just as the strict-result path does.
The host record only qualifies a candidate for the existing formal queue; it
does not establish local correctness, official pass status or score. The CLI
requires exactly one of `--strict-result` and `--host-validation`.

The metadata file contains `binary_sha256`, `binary_path`, `risks` (a list,
possibly empty), and `build_fingerprint`. The build fingerprint must include
`returncode: 0`, `files` (all eight project file hashes), `binary_sha256`, and
`payload_enabled: true`. The strict result fingerprint must match kernel and
binary hashes and include a nonempty `environment`. Build identity is a
record supplied by the trusted Coordinator, not cryptographic proof of how
a compiler produced a binary. Do not put credentials in metadata.

Optional `project_files` explicitly lists the complete build project when it
differs from the eight-file default. The dynamic service editable list is
checked against that qualified project before POST; an unknown file blocks
submission rather than silently changing the payload.

## Coordinator worker

The Coordinator is the only process allowed to run the formal client:

```bash
python3 optimization/fast_track.py \
  --root /tmp/opencode/fast-track/queue worker \
  --cli gitlabcann/cannjudge_cli.py \
  --output /tmp/opencode/fast-track/results \
  --contest op_challenge_hangxia_prelim \
  --problem quantmatmulreluquant \
  --ranking-query '西西里 的队伍'
```

The worker submits qualified snapshots serially and reconciles each submission
before proceeding to the next candidate. It uses the
existing CLI session mechanism; it never reads, logs, copies, or accepts a
Cookie value as an argument. The underlying CLI uses its default local session;
`worker`, `serve` and `reconcile` also accept `--session /path/to/session-file`.
Only the path is passed to the reviewed CLI for submit, result and ranking
requests; the worker does not read or copy the credential contents. A `submitted` queue state means only that the request
was accepted by the CLI. The resulting service response and submission-bound
score must still be verified with the formal evidence workflow before any
promotion decision. `uncertain` jobs remain auditable and are not retried
automatically, avoiding duplicate submissions after a timeout.

This worker has a process lock preventing concurrent submitters. A timeout,
unknown service response, missing submission ID, or missing submission-bound
score halts the queue and requires `reconcile`; it never retries an uncertain POST. A
verified terminal result is archived under the configured evidence root with
the uploaded-file manifest and recoverable source files. Promotion remains a
separate Coordinator decision requiring the AGENTS.md evidence gates.

### Explicit rate-limit retry

The shared `gitlabcann/cannjudge_cli.py` handles submission POST rate limits,
so both direct submissions and Fast Track use the same policy without nested
retry loops. Only HTTP 429 with an explicit, parseable server wait in seconds
and no submission-ID indication is retried: wait that duration, then resend
the identical frozen in-memory payload, at most twice per CLI invocation.
Fast Track keeps its worker lock throughout the wait; CLI messages are retained
in `worker.log`. No delay is guessed. Missing delay, exhausted retries, auth
failure, network timeout or unknown acceptance still fails closed. Interrupted
jobs are not automatically reposted. This is a refusal-specific exception,
not permission to retry accepted submissions or override `uncertain` states.

## Continuous operation and Coordinator integration

`serve` uses the same arguments as `worker`, with `--max-seconds 3600` and
`--poll-interval 60` defaults. It checks the queue periodically and stops on
unresolved outcomes; it is bounded, not an installed operating-system service.
Alternatively, launch `multi_agent_worker.py` with the optional
`--fast-track-ranking-query <team-search>` (otherwise CLI reads `team.txt`) to consume the default formal queue
at CAModel case boundaries. Existing running Coordinators are not hot-reloaded
or restarted. Do not launch a second CAModel Worker to enable this feature.

An Agent must explicitly enroll its qualified candidate. This infrastructure
does not discover arbitrary worktree edits or manufacture build/test evidence.
Credential and secret detection is not a security scanner: only supply reviewed
source and metadata. Raw CLI results/logs stay under protected output directories.
