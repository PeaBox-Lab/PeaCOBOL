# Changelog

## 1.0.0 — Release Hardening Foundations

### Added

- Rules integrity manifests: every scan and assurance report embeds `rules_manifest_hash`, a reproducible hash of the rule-definition sources.
- `peacobol rules-manifest` / `rules-verify` CLI commands for CI tamper detection.
- Signed release workflow: `peacobol sign-release` produces an immutable archive plus HMAC-SHA256 envelope; `verify-release` checks signature *and* archive bytes.
- Release envelopes require `PEACOBOL_ATTESTATION_KEY` (>= 32 bytes) and reject whitespace-bearing release names.

### Changed

- Version advanced from 0.9.0 to 1.0.0.

## 0.9.0 — Responsive Workbench Execution

### Added

- Background `TaskRunner` executes workbenches on worker threads; callbacks marshal back onto the Tk main thread.
- Indeterminate progress bar while a workbench runs, plus success/error status-bar states.
- Bilingual UI strings (English, Spanish, French, German, Chinese) through the `I18N` layer.
- Loopback-only `NetworkClient` (stdlib `urllib`, no new dependencies) for optional server-mode execution.
- Reusable widget library: `ProgressBar`, `StatusLabel`, `ErrorDialog` with actionable tips, `ResultFrame` JSON pane.
- Headless-safe GUI test suite (12 tests) covering imports, i18n, task dispatch, and busy-state locking.

### Changed

- Workbench buttons launch selected analyses against the opened project directory.
- Diagnostics, impact, test, golden, coverage, and DB2 workbenches prompt for required input files before dispatch.
- Version advanced from 0.8.0 to 0.9.0.

## 0.7.0 — Enterprise Integration Foundations

### Added

- Db2 copybook compatibility and incompatibility gates.
- Db2, CICS, and MQ resource inventories.
- Guarded offline Zowe/zOSMF submission plans.
- CycloneDX-style SBOM generation.
- Local keyed attestations and verification.
- Reproducible immutable evidence archives and dry-run retention plans.
- Enterprise resources, DB2 compatibility, and SBOM GUI views.
- Windows, native Linux, and WSL launchers.
- One-time GUI bootstrap exchange into an HttpOnly SameSite session cookie.

### Security

- Submission planning requires an enabled HTTPS allow-list target, an approved role, and a `vault://` credential reference.
- Submission planning is dry-run-only and contains no network client.
- Attestation keys require at least 32 bytes and are never persisted.
- Evidence archives reject duplicate filenames and existing outputs.
- Retention planning never deletes files.

### Changed

- Version advanced from 0.6.0 to 0.7.0.

## 0.6.0 — Test Workbench and GUI

- Copybook test generation, golden comparison, verified coverage, parser robustness, and token-protected multi-workbench GUI.

## 0.5.0 — Assurance and Change Impact

- Dependency graphs, field/flow inventories, structural impact, SARIF, gates, and integrity hardening.

## 0.4.0 — Diagnostics Center

- Spool analysis, local catalogs, source correlation, checklists, and failure bundles.

## 0.3.0 — Build Profiles and IBM JCL

- Versioned profiles, JCL generation, diagnostics, manifests, and policy gates.

## 0.2.0 — Data Integrity and Audit Workbench

- Hierarchical copybooks, records, evidence, auditing, and safer local operation.

## 0.1.0

- Initial project manager, analyzer, copybook inspector, local UI, GnuCOBOL adapter, evidence generator, sample, and tests.
