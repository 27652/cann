# Independent architecture trial: local L0C K accumulation

## Single hypothesis

Keep one Cube output tile in L0C across multiple safe K chunks and materialize
one INT32 tile only after the final chunk. This targets repeated GM read/atomic
accumulation for large K. It is not combined with the FIFO or scale-owner
prototypes.

## Scope and evidence

The path is guarded to tiles fitting one configured base tile and K below the
first guarded overflow boundary; other shapes retain the baseline path. The
independent benchmark target compiled under CANN 9.1/dav-2201. No device
correctness, performance, or official score is claimed.

## Risk and decision

`Iterate(enPartialSum)` compiles, but the local Matmul implementation resets
its scheduler in SetTensorA/SetTensorB. L0C retention across those resets is
not established. Treat this as an API probe; do not submit until device output
visibility, tails, and K accumulation are proven.
