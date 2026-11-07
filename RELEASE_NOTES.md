# PeaCOBOL 0.4.0 Release Notes

## Release theme

**Diagnostics Center**

This release turns compiler and runtime output into repeatable local investigation evidence without submitting jobs, accessing credentials, or asserting unapproved environment-specific meanings.

## Delivered

- Spool return-code and failed-step extraction.
- Abnormal-termination and COBOL file-status marker extraction.
- Reuse of normalized GnuCOBOL and IBM compiler diagnostics.
- Bounded compiler/spool-to-source correlation with source hashes.
- Extensible, validated site catalogs with explicit unknown-code fallback behavior.
- Deterministic investigation and remediation checklists.
- Reproducible failure bundles with spool and bundle SHA-256 hashes.
- CLI commands `knowledge`, `diagnose`, and `failure-bundle`.

## Validation summary

- 46 automated tests pass: 32 retained regression tests and 14 new 0.4.0 tests.
- Python source compilation passes.
- Tests cover spool extraction, clean and failed return codes, input-size limits, site catalog extension and validation, path traversal, symlink rejection, bounded source context, checklist generation, and repeatable bundle hashing.
- End-to-end CLI validation covers diagnosis, knowledge lookup, failure-bundle output, and deterministic regeneration.
- An independent security re-review reported no remaining security vulnerabilities after remediation.

## Boundary

The built-in catalogs provide safe fallback investigation guidance only. Environment-specific ABEND and file-status interpretations must be supplied through approved project-local catalog files.
