# Changelog

## 0.3.0 — Build Profiles and IBM JCL

### Added

- Versioned development, release, banking, and aerospace profiles.
- Validated project-level profile overrides.
- IBM Enterprise COBOL compile/link/run JCL generation.
- GnuCOBOL and IBM diagnostic normalization.
- Reproducible build manifests with source and artifact hashes.
- Policy gates for finding severity, build results, warnings, and evidence.
- Profile-driven encoding, binary byte order, and signed binary decoding.
- `profiles`, `jcl`, and `gate` CLI commands.

### Changed

- Build, record decode, and record conversion workflows accept named profiles.
- Scan, build, doctor, evidence, copybook, and record schemas advanced where their payloads changed.
- New project configuration exposes all four profiles and defaults to development.
- Version advanced from 0.2.0 to 0.3.0.

## 0.2.0 — Data Integrity and Audit Workbench

- Hierarchical copybook model, nested group layout, `OCCURS`, and validated `REDEFINES` overlays.
- COMP-3 pack/unpack, fixed-record decoding, JSONL/CSV conversion, bounded hex views, reproducible evidence, and hash-chained action auditing.
- Safer scanning, builds, local UI boundaries, and 16-test validation suite.

## 0.1.0

- Initial project manager, analyzer, copybook inspector, local UI, GnuCOBOL adapter, evidence generator, sample, and tests.
