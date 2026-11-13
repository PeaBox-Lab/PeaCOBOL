# PeaCOBOL 1.1.0 Release Notes

## Release theme

**Validation and Release Evidence**

This release adds assembled release evidence bundles and automated release validation gates while deliberately keeping all analysis, evidence, and signing local.

## Delivered

- Release evidence bundle assembly from scan reports, SBOM, attestations, and immutable exports into a single archive.
- Release validation gates: version consistency, launcher syntax, and packaging checks before a release is tagged.

## Validation summary

- The full automated test suite passes, including the release-evidence tests.

## Boundary

No network connection, no job submission, and no public-key release signing is performed. Signing uses a local environment-held HMAC key.

# PeaCOBOL 1.0.0 Release Notes

## Release theme

**Release Hardening Foundations**

This release adds reproducible rules-integrity manifests, CI tamper-detection commands, and an HMAC-signed immutable release workflow while deliberately keeping all analysis, evidence, and signing local.

## Delivered

- Rules integrity manifests: every scan and assurance report embeds `rules_manifest_hash`, a reproducible hash of the rule-definition sources.
- `peacobol rules-manifest` / `rules-verify` CLI commands for CI tamper detection.
- Signed release workflow: `peacobol sign-release` produces an immutable archive plus HMAC-SHA256 envelope; `verify-release` checks signature *and* archive bytes.
- Release envelopes require `PEACOBOL_ATTESTATION_KEY` (>= 32 bytes) and reject whitespace-bearing release names.

## Validation summary

- The full automated test suite passes, including the release-hardening tests for rules integrity and signed-release verification.

## Boundary

No network connection, no job submission, and no public-key release signing is performed. Signing uses a local environment-held HMAC key.

# PeaCOBOL 0.7.0 Release Notes

## Release theme

**Enterprise Integration Foundations**

This release adds static enterprise inventories, guarded offline integration plans, supply-chain evidence, and one-click GUI launchers while deliberately keeping remote submission outside the application.

## Delivered

- Db2 DDL/copybook compatibility analysis and incompatibility gate.
- Db2, CICS, and MQ resource inventories.
- HTTPS, role, allow-list, and vault-reference validation for dry-run Zowe/zOSMF submission plans.
- CycloneDX-style SBOM output.
- In-toto-style local attestations with optional strong HMAC signing and verification.
- Reproducible content-addressed evidence archives.
- Dry-run retention planning.
- Enterprise resource, DB2, and SBOM GUI workbenches.
- Windows `start.bat`, native Linux `start-linux.sh`, and WSL `start-linux.bat` launchers.

## Validation summary

- 105 automated tests pass: 92 retained tests and 13 new 0.7.0 tests.
- Python source compilation and Linux launcher syntax checks pass.
- Tests cover DB2 compatibility, resource inventories, guarded submission plans, SBOM, attestations, immutable exports, retention plans, launchers, and enterprise GUI views.
- End-to-end CLI validation covers incompatibility gates, inventory hashes, submission dry-runs, supply-chain output, and archive integrity.
- Independent security review found no vulnerabilities, and correctness certification found no significant issues after remediation.

## Boundary

No enterprise network connection or mainframe job submission is performed. All enterprise features in this release are local analysis, evidence, or validation plans.
