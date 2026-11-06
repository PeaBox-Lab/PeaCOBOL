# Changelog

## 0.2.0 — Data Integrity and Audit Workbench

### Added
- Hierarchical copybook model, nested group layout, `OCCURS`, and validated `REDEFINES` overlays.
- COMP-3 pack/unpack, fixed-record decoding, JSONL/CSV conversion, and bounded hex views.
- Hash-chained audit events for successful and failed CLI actions and UI scans.
- Audit verification command.
- Reproducible evidence schema v2 and scan/build/copybook schemas v2.
- Project-root boundary for the local UI and browser security headers.

### Fixed
- Incorrect offsets after `OCCURS` and `REDEFINES`.
- Evidence recursively hashing a previous evidence output.
- Build target collisions for same-named programs in different directories.
- Unbounded compiler runs and diagnostics.
- Scanning generated directories and following source symlinks.
- COBOL comment lines creating false findings.
- Project initialization overwriting an existing sample source file.

### Changed
- Version advanced from the supplied working implementation's 0.1.0 to 0.2.0.
- Generated, report, cache, and audit directories are excluded from source inventories.

## 0.1.0
- Initial project manager, analyzer, copybook inspector, local UI, GnuCOBOL adapter, evidence generator, sample, and tests.
