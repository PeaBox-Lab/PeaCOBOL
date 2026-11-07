# PeaCOBOL 0.1.0 Application and Process Audit
## Executive conclusion
The supplied implementation was a functional development preview, but its four-test suite did not exercise its highest-risk claims. The most serious defects were incorrect record layouts for `OCCURS` and `REDEFINES`, non-reproducible evidence after an evidence file existed inside the project, an unconstrained UI path selector, and no durable record of actions. Version 0.2.0 addresses these foundations before remote or regulated integrations are attempted.
## Audited surfaces
| Surface | 0.1.0 finding | Risk | 0.2.0 treatment |
|---|---|---:|---|
| Project initialization | Re-running initialization overwrote the sample program and advertised placeholder profiles as if configured. | Medium | Initialization is idempotent for existing source and emits explicit 0.2 profiles. |
| Doctor | Basic presence check only; no structured recommendations. | Low | Schema and actionable readiness guidance added. |
| Source scan | Scanned generated directories, followed broad recursive input, and allowed comment false positives. | High | Generated/cache/audit directories and symlinks are skipped; file/count limits and comment handling added. |
| Assurance rules | Line heuristics could not understand multiline semantics and had low test coverage. | Medium | Existing rules retained with deterministic boundaries and dynamic-call visibility; deeper flow analysis remains roadmap work. |
| Copybook inspection | Ignored groups and `OCCURS`; assigned a redefining item the next offset instead of its target's offset. | Critical | Hierarchical layout, repeated storage, target validation, and overlay offsets implemented and tested. |
| Record handling | Roadmap capability was absent. | High | COMP-3, display/binary decoding, EBCDIC support, fixed-record conversion, and hex views added. |
| Build | No timeout, output collisions by stem, no copybook include paths, and unbounded captured diagnostics. | High | Timeouts, relative targets, include paths, and diagnostic caps implemented without shell execution. |
| Evidence | Included prior evidence files, absolute project path, environment-specific doctor data, and potentially generated content. | High | Stable project identity, generated-content exclusions, explicit output exclusion, sorted inventory, and manifest hash added. |
| CLI output | Direct writes were not atomic and failures were not structured. | Medium | Atomic UTF-8 writes and structured error output added. |
| Action auditing | No record of who ran which operation or whether it succeeded. | High | Every CLI action and UI scan produces a hash-chained local event; verification detects tampering. |
| Local UI | Accepted arbitrary local paths, had no root boundary, and lacked browser hardening headers. | High | Administrator-selected root, traversal rejection, CSP, nosniff, and no-referrer headers added. |
| Test process | Four tests covered only storage, a flat copybook, one scan signal, and file creation. | High | Coverage expanded across layouts, codecs, evidence, audit integrity, exclusions, initialization, and compiler absence. |
## Remaining limitations
\- The analyzer remains a deterministic text analyzer, not a standards-complete COBOL parser.
\- `OCCURS DEPENDING ON`, level 66 RENAMES, level 88 condition names, national data, and all edited PIC combinations are not fully modeled.
\- Binary endianness and compiler-specific representation can vary by platform and must become profile-driven.
\- Audit logs are tamper-evident but not signed or stored immutably; an administrator with filesystem access can replace the entire log.
\- Local build isolation is not a sandbox. Compilation should run in a constrained worker before processing untrusted projects.
\- The UI has no authentication because it remains loopback-only. Authentication is required before any shared binding.
\- No IBM Enterprise COBOL, z/OSMF, Zowe, Db2, CICS, or MQ environment was available in the supplied context, so those integrations were neither implemented nor claimed as validated.
