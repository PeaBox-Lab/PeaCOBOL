# Changelog

## 0.6.0 — Test Workbench and GUI

### Added

- Copybook-driven typical, minimum, maximum, and invalid record cases.
- COBOL Check-compatible starter generation.
- Golden-master binary comparison and difference gates.
- Coverage import with verified evidence manifests, canonical source identity, source-derived denominators, integrity hashes, and threshold gates.
- Seven-workbench server-rendered GUI covering scan, assurance, diagnostics, impact, tests, golden comparison, and coverage.
- `test-cases`, `golden`, and `coverage` CLI commands.

### Security

- GUI remains loopback-only, validates the Host header, requires a random per-launch token, and rejects absolute paths, traversal, and symlink components.
- GUI is script-free and sends CSP, nosniff, no-referrer, frame-ancestor, and no-store protections.
- Coverage inputs are size-bounded, schema-validated local JSON.

### Changed

- Version advanced from 0.5.0 to 0.6.0.

## 0.5.0 — Assurance and Change Impact

- Dependency graphs, field and flow inventories, structural impact analysis, SARIF, gates, profile hardening, contained builds, and concurrent audit integrity.

## 0.4.0 — Diagnostics Center

- Spool analysis, validated local catalogs, source correlation, checklists, and hashed failure bundles.

## 0.3.0 — Build Profiles and IBM JCL

- Versioned profiles, IBM JCL generation, normalized diagnostics, build manifests, and policy gates.

## 0.2.0 — Data Integrity and Audit Workbench

- Hierarchical copybooks, fixed-record tools, evidence, auditing, and safer local operation.

## 0.1.0

- Initial project manager, analyzer, copybook inspector, local UI, GnuCOBOL adapter, evidence generator, sample, and tests.
