# PeaCOBOL Roadmap

## Delivered: 0.2.0 — Data Integrity and Audit Workbench

- Correct nested copybook offsets, `OCCURS`, and `REDEFINES`.
- COMP-3 and fixed-record decoding, EBCDIC support, JSONL/CSV conversion, and hex inspection.
- Hash-chained action auditing and reproducible evidence.

## Delivered: 0.3.0 — Build Profiles and IBM JCL

- Versioned development, release, banking, and aerospace profiles.
- IBM Enterprise COBOL compile/link/run JCL generation.
- Compiler diagnostic normalization and hashed build manifests.
- Profile-driven binary representation and encoding rules.
- Policy gates for warnings, findings, builds, and missing evidence.

## Delivered: 0.4.0 — Diagnostics Center

- ABEND and COBOL file-status knowledge bases.
- Spool return-code extraction and compiler/source correlation.
- Failure bundles with source context and integrity hashes.
- Deterministic investigation and remediation checklists.

## Delivered: 0.5.0 — Assurance and Change Impact

- Program call graph and copybook dependency graph.
- Copybook field-level change-impact analysis.
- Field read/write inventory and control-flow graph.
- Bounds, subscript, dangerous movement, and data-flow rules.
- SARIF export and configurable severity gates.

## 0.6.0 — Test Workbench

- COBOL Check integration.
- Boundary and invalid-data generation from copybooks.
- Golden-master regression comparison.
- Coverage import and evidence linkage.
- Property-based and parser-fuzz test suites.

## 0.7.0 — Enterprise Integrations

- Db2 schema compatibility and bind-plan inventory.
- CICS and MQ resource inventories.
- Optional Zowe CLI/zOSMF submission behind explicit allow-lists, TLS verification, RBAC, and vault-managed credentials.
- SBOM, signed attestations, immutable evidence export, and retention policies.

## 1.0.0 — Validated Enterprise Platform

Release only after independent security review, representative GnuCOBOL and z/OS estate validation, threat modeling, performance baselines, recovery testing, compatibility matrices, and documented certification evidence.
