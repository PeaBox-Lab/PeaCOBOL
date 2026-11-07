# PeaCOBOL 0.3.0 Release Notes

## Release theme

**Build Profiles and IBM JCL**

This release turns the 0.2.0 data and audit foundation into a controlled build workflow. It adds explicit environment profiles, deterministic JCL generation, comparable diagnostics, hashed build manifests, and policy decisions suitable for automation.

## Delivered

- Four validated profiles: development, release, banking, and aerospace.
- Profile-aware GnuCOBOL flags, data encoding, binary representation, IBM compiler options, and gate thresholds.
- IBM Enterprise COBOL compile/link/run JCL generation with strict dataset/member validation and an optional no-run mode.
- Diagnostic normalization for GnuCOBOL and IBM message formats.
- Build manifest schema `peacobol-build-manifest-1` with source and compiled-artifact hashes.
- Policy schema `peacobol-policy-1` covering findings, build outcome, warnings, and evidence.
- CLI commands `profiles`, `jcl`, and `gate`; profile support for `build`, `decode`, and `convert`.

## Validation summary

- 32 automated tests pass: 16 retained regression tests and 16 new 0.3.0 tests.
- Python source compilation passes.
- Profile override validation, binary byte order, JCL safety, diagnostic normalization, build manifest hashing, and release gates are covered.
- End-to-end CLI checks cover profile inspection, JCL generation, scan/evidence generation, and gate exit semantics.
- Missing GnuCOBOL remains a controlled capability limitation; no alternate compiler or shell-based fallback is attempted.

## Boundary

Generated JCL is never submitted. IBM datasets, compiler libraries, procedure names, and organization-specific JOB card values must be reviewed and adjusted for the target z/OS estate.
