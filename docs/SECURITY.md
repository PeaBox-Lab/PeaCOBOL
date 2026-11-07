# Security Model
## Implemented controls
\- Local-first and offline-capable; no telemetry or source upload.
\- Analysis never executes project source.
\- Compiler invocation uses a fixed argument array with `shell=False` and a bounded timeout.
\- Source inventories skip symlinks, generated directories, caches, reports, and audit content.
\- File-size and project-file-count limits reduce accidental resource exhaustion.
\- UI binds to loopback and enforces an administrator-selected root directory.
\- Browser responses include a restrictive Content Security Policy, nosniff, no-referrer, and frame-ancestor protections.
\- CLI and UI actions produce hash-chained audit events; verification detects line modification, deletion within the chain, and reordering.
\- Evidence manifests are deterministic for unchanged included inputs and carry an overall manifest hash.
## Security boundaries
\- Audit records are tamper-evident, not cryptographically signed or remotely anchored.
\- GnuCOBOL compilation is a local process and is not sandboxed.
\- `--no-audit` is an explicit operator escape hatch and should be disabled by organizational wrappers in regulated environments.
\- The loopback UI has no user authentication and must not be exposed through port forwarding or a shared bind.
\- Text and data parsers require additional fuzzing before handling hostile inputs at scale.
## Required before regulated production
Add sandboxed build workers, signed releases and rules, vault-managed credentials, RBAC, immutable audit storage, SAST/DAST, dependency and license scanning, threat modeling, fuzzing, independent validation, disaster recovery, retention controls, and sector-specific certification evidence.

## 0.3.0 build-control additions

- Built-in profiles are immutable at runtime; project overrides are merged from local JSON and validated before use.
- JCL program members and dataset names are allow-list validated before generation.
- JCL generation is offline and has no submission, credential, network, or remote execution path.
- Policy gates produce explicit failed-check identifiers and a non-zero CLI result for automation.
- Build manifests avoid absolute project paths and hash source and available output artifacts.
- Normalized diagnostics are bounded by the existing compiler output limit.

## 0.4.0 diagnostics controls

- Spool files are limited to 10 MiB and checked before full reads.
- Symlinked spool files are rejected.
- Correlated source paths must resolve beneath the selected project root and must be regular non-symlinked files.
- Source files larger than 5 MiB are not included in failure context.
- Context excerpts are bounded to eight lines on either side of a source reference.
- Site-specific catalog entries are local JSON, shape-validated, and never fetched remotely.
- Failure bundles are deterministic and contain spool, source, and bundle integrity hashes.

- Project profile compiler flags are allow-listed; execution and argument-forwarding options are rejected.
- Audit logs reject symlink path components and use no-follow file opening where the platform supports it.

## 0.5.0 assurance controls

- Assurance analysis reuses bounded, non-symlinked source discovery and excludes generated, audit, cache, and report directories.
- Graph identifiers and SARIF locations come from discovered local source paths; no source content is uploaded.
- Severity and change-impact gates are deterministic and produce a distinct non-zero exit status without executing source code.
- Copybook impact files are parsed locally and their exact input hashes are recorded in the report.
- Findings are review signals rather than claims of exploitability or runtime certainty.

- Release, banking, and aerospace profile overrides cannot weaken inherited finding, warning, or evidence gates.
- Build output directories and target components reject symlinks and remain contained beneath the project build root.
- Audit append and verification operations share an inter-process lock over complete hash-chain transactions.
