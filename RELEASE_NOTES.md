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
