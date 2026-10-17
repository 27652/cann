# Independent architecture trial: row scale-owner reduction

## Single hypothesis

In N-sharded mode, one Vector participant owns each row reduction, computes
yScale once, and publishes compact `{scale,isZeroRow}` metadata. Other
participants only quantize their N slice. This removes duplicate reduction and
scale work at the cost of metadata traffic and extra barriers.

## Scope and evidence

The candidate changes only the existing wide-row shard path; Cube scheduling,
K splitting, and the complete-row path are unchanged. Its benchmark target
compiled under CANN 9.1/dav-2201. No device correctness, performance, or
official score is claimed.

## Risk and decision

Metadata GM visibility, idle-participant collective ordering, zero rows, tails,
and the extra barriers remain unproven. Keep this candidate separate and run a
targeted wide-row smoke was originally planned before formal submission.

## Verified formal feedback (2026-10-17)

The existing frozen payload was independently submitted as
`6ad3343f193e507d8e95990c`: Pass 15/15, exact-ID ranking score **16.60**.
The bundle `evidence/formal/scale-owner-6ad3343f/` validates offline. Not
promoted. No duplicate POST was performed during this verification session.
`targeted_checks.py` now passes 125 shard/owner/workspace configurations for
the exact frozen source. These are host/static checks, not device proof.
No local device smoke is claimed; the existing submission used Fast Track.
