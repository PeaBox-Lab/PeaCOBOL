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

## Delivered: 0.6.0 — Test Workbench and GUI
- COBOL Check integration.
- Boundary and invalid-data generation from copybooks.
- Golden-master regression comparison.
- Coverage import and evidence linkage.
- Property-based and parser-fuzz test suites.

## Delivered: 0.7.0 — Enterprise Integration Foundations
- Db2 schema compatibility and bind-plan inventory.
- CICS and MQ resource inventories.
- Optional Zowe CLI/zOSMF submission behind explicit allow-lists, TLS verification, RBAC, and vault-managed credentials.
- SBOM, signed attestations, immutable evidence export, and retention policies.

## Delivered: 0.8.0 — Desktop GUI and Enhanced Security
- Desktop GUI interface for project management and workbenches.
- Reusable widget library (ProgressBar, StatusLabel, ErrorDialog, ResultFrame).
- Authentication prompts with per-session tokens.
- Headless-safe automated GUI test suite.

## Delivered: 0.9.0 — Responsive Workbench Execution
- Background task runner keeps the Tk main loop free during scans.
- Indeterminate progress bar plus status bar feedback for every workbench.
- Bilingual UI (English, Spanish, French, German, Chinese) via the i18n layer.
- Loopback server client (urllib-only, no new dependencies) for optional server mode.
- Workbench launchers accept required file picks before execution starts.
- Theme manager with light, dark, and high-contrast palettes and four font scales.
- One-click result export to `reports/gui/` with hash-chained audit events and a 10 MiB cap.

## Delivered: 1.0.0 — Release Hardening Foundations
- Rules integrity manifests: every scan and assurance report embeds a reproducible `rules_manifest_hash` of the rule-definition sources.
- `peacobol rules-manifest` / `rules-verify` CLI commands for CI tamper detection.
- Signed release workflow: `peacobol sign-release` produces an immutable archive plus HMAC-SHA256 envelope; `verify-release` checks signature and archive bytes.
- Release envelopes require `PEACOBOL_ATTESTATION_KEY` (>= 32 bytes) and reject whitespace-bearing release names.

## 1.0.0 — Validated Enterprise Platform
Offline controls now in place: rules-integrity manifests embedded in every scan/assurance report, signed-release signing and verification commands, and CI-usable `rules-manifest`/`rules-verify`. Remaining gates before tagging 1.0.0 (external, not automatable here): independent security review, representative GnuCOBOL and z/OS estate validation, threat modeling, performance baselines, recovery testing, compatibility matrices, and documented certification evidence.