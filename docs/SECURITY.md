# Security Model

- Local-first and offline-capable
- No source upload, telemetry, embedded credentials, or remote scripts
- No shell invocation; compiler arguments are passed as a fixed array
- Read-only analysis by default
- Explicit build action
- SHA-256 evidence inventory

Before regulated production use, add authentication for shared deployments, sandboxed workers, signed rules and releases, secret-vault integration, role-based access, immutable audit storage, SAST/DAST, dependency scanning, threat modeling, independent validation, and sector-specific certification evidence.
