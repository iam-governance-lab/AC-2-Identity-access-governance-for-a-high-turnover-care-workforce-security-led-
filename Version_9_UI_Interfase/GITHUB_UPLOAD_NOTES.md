# GitHub source package

This is a cleaned copy of Sunhaven Version 9 Final for source control.

Removed: macOS metadata, Python caches, generated evidence and reports, the
local portal database and its ledger key/head. Source, tests, docs, static
assets, sample configuration and demo input data are retained. The original/
folder is needed by the launcher and tests; it is intentionally retained.

Extract this ZIP and commit the extracted files using Git/VS Code. Uploading
the ZIP itself stores an archive, rather than making the source browsable.
The package contains many files, so Git/VS Code is preferable to browser upload.

The local database is recreated when the demo starts. Saved local demo changes
are not included. Run from this folder using Python 3.12+: `python3 run.py`.

Historical docs still refer to excluded evidence files. Existing test reports
are historical; no full application test suite was rerun for this cleanup.

The original and release manifests have been regenerated for the retained
files. They verify this cleaned package, not the complete original archive.
Original source files retained in this package have not been edited.
