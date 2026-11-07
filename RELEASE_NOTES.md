# PeaCOBOL 0.6.0 Release Notes

## Release theme

**Test Workbench and GUI**

This release makes PeaCOBOL's local analysis workflows accessible through both automation-safe CLI commands and a secure multi-workbench browser interface.

## Delivered

- Copybook-driven boundary and invalid record generation.
- COBOL Check-compatible starter generation.
- Golden-master binary comparison with first-difference location and hashes.
- Coverage import, evidence linkage, integrity hashing, and minimum threshold gates.
- A seven-workbench loopback GUI for scanning, assurance, diagnostics, impact, tests, golden comparison, and coverage.
- Server-rendered, script-free pages with root containment, symlink rejection, strict loopback Host validation, a random per-launch token, CSP, no-referrer, nosniff, frame protection, and no-store caching.
- CLI commands `test-cases`, `golden`, and `coverage`.

## Validation summary

- 92 automated tests pass: 69 retained regression tests and 23 new 0.6.0 tests.
- Python source compilation passes.
- GUI tests run a live loopback server and validate navigation, workbench output, security headers, traversal rejection, symlink rejection, and 404 behavior.
- Test Workbench tests cover generated records, starter output, golden differences, coverage normalization, invalid input, and deterministic malformed-copybook robustness.
- End-to-end CLI validation covers all three new commands and their gate exit semantics.
- Independent certification found no significant remaining issues after review-driven parser, coverage, golden-comparison, signed-boundary, and GUI security fixes.

## Boundary

The GUI is intentionally unauthenticated and loopback-only. Do not expose it through shared bindings, reverse proxies, tunnels, or port forwarding.
