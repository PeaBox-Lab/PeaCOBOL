# Architecture

PeaCOBOL 0.6.0 adds a testing and presentation layer while preserving the prior deterministic engines:

1. **Copybook test generator** creates bounded record variants directly from computed field layout and representation.
2. **Golden comparator** performs byte-level equality, first-difference detection, and integrity hashing without executing tested programs.
3. **Coverage importer** validates bounded JSON line coverage, normalizes paths and counts, links an optional evidence hash, and computes a coverage hash.
4. **GUI controller** maps seven read-oriented workbenches to existing analysis functions through server-rendered HTML.
5. **Path boundary** resolves only non-symlinked relative files and directories beneath the configured GUI root.
6. **Browser boundary** uses loopback binding, no scripts, restrictive CSP, no-store caching, no-referrer, nosniff, and frame denial.
7. **Existing assurance, diagnostics, impact, build, evidence, and audit engines** remain reusable by both CLI and GUI.

The GUI does not provide remote submission, arbitrary commands, source editing, authentication, or shared binding.
