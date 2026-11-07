# Architecture

PeaCOBOL 0.4.0 separates deterministic analysis, data interpretation, build control, diagnostics, policy, evidence, and audit concerns:

1. **Source assurance** discovers programs, calls, copy references, paragraphs, and deterministic findings without executing project code.
2. **Copybook and record workbench** computes layouts and decodes fixed records with profile-driven representation.
3. **Profile and build engines** validate configuration, generate IBM JCL, invoke GnuCOBOL safely, normalize diagnostics, and hash build artifacts.
4. **Spool parser** extracts bounded job-step, return-code, abnormal-termination, file-status, compiler, and source-reference signals.
5. **Knowledge layer** merges safe built-in fallback guidance with validated project-local diagnostic catalogs.
6. **Investigation engine** correlates spool signals with bounded source excerpts and generates an ordered deterministic checklist.
7. **Failure-bundle engine** hashes the original spool and canonical diagnosis payload for repeatable evidence.
8. **Policy, evidence, and audit engines** enforce release checks, create reproducible manifests, and append hash-linked action records.
9. **Local UI** remains read-only, loopback-bound, and restricted to a configured project root.

Remote execution, credential handling, mainframe submission, and environment-specific operational assertions remain outside this trust boundary.
