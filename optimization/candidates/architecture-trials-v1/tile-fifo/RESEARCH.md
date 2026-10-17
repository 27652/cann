# Independent architecture trial: bounded tile FIFO

## Single hypothesis

Use a bounded two-slot paired AIC/AIV FIFO: AIC produces a row job, AIV
consumes it, and ready/free events provide backpressure before slot reuse. This
targets global producer-then-consumer idle time without adding a dynamic scalar
scheduler.

## Scope and evidence

The FIFO is gated to large-M, narrow-enough-N workloads; other shapes retain
the baseline path. The independent benchmark target compiled under
CANN 9.1/dav-2201. No device correctness, performance, or official score is
claimed.

## Risk and decision

Event protocol, slot reuse ordering, AIC/AIV pairing, tail rows, and
single-launch liveness remain unproven. The current prototype has complete-row
job granularity, not N-tile publication, so it must not be described as a
fully asynchronous global work queue. First run a small multi-job exact smoke,
then measure cycles was the original local validation plan.

## Verified formal feedback (2026-10-17)

The existing frozen payload submission `6ad335a8193e507d8e985b8b` completed
Pass 15/15. A fresh service result query and exact-ID ranking query confirmed
score **16.89**. Evidence `evidence/formal/tile-fifo-6ad335a8/` validates;
the decision checker reports strict improvement over verified 16.69.
`targeted_checks.py` passes 150 row-ownership/FIFO reuse/drain models.
No new CAModel smoke or task-cycle measurement was performed in this session.

While this verification was running, another workspace process replaced root
`kernel.asc` with the identical official FIFO source. All eight root project
files match the recovered service source. This session did not overwrite the
root. The old 16.66 source remains recoverable; this candidate's known event,
tail, numerical-boundary and local-device-coverage risks remain recorded above.
