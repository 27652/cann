# Formal evaluation evidence

This directory contains metadata and hashes only; it must remain mode `0700`.
It must not contain cookies or raw API payloads. The raw historical result and
ranking snapshot remain at the protected paths recorded in `manifest.txt`.

The eight editable-file hashes in `submission-files.sha256` identify the
historical submission. Reconstructing its contents still requires the
protected external result snapshot named in `manifest.txt`; hashes alone are
not a source backup. The current root is not that submission because its
`kernel.asc` hash differs.
