# Changelog

## 0.4.0 — Diagnostics Center

### Added

- Spool step, return-code, abnormal-termination, file-status, compiler-diagnostic, and source-reference extraction.
- Validated project-local ABEND and file-status catalogs with explicit unknown-code fallback entries.
- Bounded source correlation with SHA-256 hashes.
- Deterministic investigation checklists.
- Reproducible failure bundles with spool and bundle hashes.
- `knowledge`, `diagnose`, and `failure-bundle` CLI commands.

### Security

- Spool inputs are size-checked before reading and symlinked spool files are rejected.
- Correlated source files must be regular non-symlinked files beneath the project root.
- Source context is bounded to eight lines on each side.
- Catalog keys and content shapes are validated before use.
- Project-controlled compiler flags are restricted to a safe allow-list.
- Audit log paths reject symlink components and final files are opened with no-follow protection where supported.

### Changed

- Version advanced from 0.3.0 to 0.4.0.

## 0.3.0 — Build Profiles and IBM JCL

- Versioned profiles, IBM JCL generation, compiler diagnostic normalization, hashed build manifests, profile-driven data representation, and policy gates.

## 0.2.0 — Data Integrity and Audit Workbench

- Hierarchical copybooks, fixed-record tools, reproducible evidence, hash-chained auditing, safer scanning/build execution, and loopback UI controls.

## 0.1.0

- Initial project manager, analyzer, copybook inspector, local UI, GnuCOBOL adapter, evidence generator, sample, and tests.
