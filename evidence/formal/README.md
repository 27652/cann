# Formal evaluation evidence

This directory contains allowlisted result metadata, hashes and recoverable
submitted sources; it must remain mode `0700`. It must not contain cookies or
raw API payloads. Original snapshots remain outside the repository at the
protected paths recorded in `manifest.txt`.

The eight editable-file hashes in `submission-files.sha256` identify the
historical submission. Its eight source files are now independently preserved
in `historical-6ad2872c/source/`; recovery no longer depends on temporary files.
`historical-6ad2872c/evidence.json` binds submission ID, 15 passing cases,
ranking score and source hashes, and records original snapshot SHA256 values.
The current root is not that submission because its `kernel.asc` hash differs.

Offline verification from the project root:

```bash
python3 evidence/formal_evidence.py validate evidence/formal/historical-6ad2872c
python3 evidence/formal_evidence.py decide <candidate-bundle> --best evidence/formal/historical-6ad2872c
```

`decide` only checks eligibility against the supplied best bundle; it neither
discovers the global historical maximum nor overwrites the working tree.
Metadata validation is not cryptographic authentication of official results;
only use bundles recovered from trusted, previously checked official snapshots.
