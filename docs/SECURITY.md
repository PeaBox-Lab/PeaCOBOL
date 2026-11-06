# Security Model

## Implemented controls

- Local-first and offline-capable; no telemetry or source upload.
- Analysis never executes project source.
- Compiler invocation uses a fixed argument array with `shell=False` and a bounded timeout.
- Source inventories skip symlinks, generated directories, caches, reports, and audit content.
- File-size and project-file-count limits reduce accidental resource exhaustion.
- UI binds to loopback and enforces an administrator-selected root directory.
- Browser responses include a restrictive Content Security Policy, nosniff, no-referrer, and frame-ancestor protections.
- CLI and UI actions produce hash-chained audit events; verification detects line modification, deletion within the chain, and reordering.
- Evidence manifests are deterministic for unchanged included inputs and carry an overall manifest hash.

## Security boundaries

- Audit records are tamper-evident, not cryptographically signed or remotely anchored.
- GnuCOBOL compilation is a local process and is not sandboxed.
- `--no-audit` is an explicit operator escape hatch and should be disabled by organizational wrappers in regulated environments.
- The loopback UI has no user authentication and must not be exposed through port forwarding or a shared bind.
- Text and data parsers require additional fuzzing before handling hostile inputs at scale.

## Required before regulated production

Add sandboxed build workers, signed releases and rules, vault-managed credentials, RBAC, immutable audit storage, SAST/DAST, dependency and license scanning, threat modeling, fuzzing, independent validation, disaster recovery, retention controls, and sector-specific certification evidence.
