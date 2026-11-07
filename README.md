# PeaCOBOL 0.6.0

PeaCOBOL is a local-first COBOL data, development, diagnostics, assurance, change-impact, and testing toolkit. Version 0.6.0 is the **Test Workbench and GUI** release.

## New Test Workbench

- Copybook-driven typical, minimum, maximum, and invalid fixed-record cases
- Deterministic record hex, decoded value intent, source hash, and cases hash
- COBOL Check-compatible starter program generation
- Byte-for-byte golden-master comparison with hashes and first-difference offset
- Normalized JSON line-coverage import, evidence linkage, integrity hash, and minimum-coverage gate
- Deterministic malformed-copybook robustness tests

## New GUI interface

Launch the loopback-only interface:

```bash
peacobol-ui --root /path/to/approved/projects
```

Open the tokenized URL printed at startup, such as `http://127.0.0.1:8765/?token=<random-session-token>`. Every request requires that launch token and a loopback `Host` header. The GUI provides seven workbenches:

1. **Scan** — project inventory and baseline findings
2. **Assurance** — graphs, field inventories, findings, and severity gates
3. **Diagnostics** — spool analysis, source context, and investigation checklist
4. **Change impact** — field-level copybook comparison
5. **Test cases** — generated records and COBOL Check-compatible starter text
6. **Golden compare** — binary regression comparison
7. **Coverage** — coverage summary, evidence linkage, and integrity details

All user paths are relative to the administrator-selected root. Absolute paths, traversal, and symlink paths are rejected. The GUI binds only to `127.0.0.1`, uses server-rendered HTML with no scripts, sends a restrictive Content Security Policy, prevents framing and referrer leakage, and disables browser caching.

## CLI examples

Generate test cases:

```bash
peacobol test-cases copybooks/ACCOUNT.cpy --cobol-check-program PAYMENT -o cases.json
```

Compare golden outputs:

```bash
peacobol golden actual.dat expected.dat --fail-on-difference -o golden.json
```

Import coverage and require at least 85%:

```bash
peacobol coverage coverage.json --evidence-manifest reports/evidence.json --project . --minimum 85 -o coverage-report.json
```

A failed golden or coverage gate exits with status 3.

## Coverage input

Coverage import accepts bounded JSON in this shape:

```json
{
  "lines": [
    {"file": "src/PAYMENT.cbl", "line": 10, "hits": 3},
    {"file": "src/PAYMENT.cbl", "line": 11, "hits": 0}
  ]
}
```

## Boundaries

Generated test cases are structural boundary aids, not complete business-rule tests. The COBOL Check output is a starter program and does not invoke or bundle COBOL Check. Coverage gates verify the evidence manifest and current project hashes, derive the denominator from verified nonblank source lines, and do not execute source code. The GUI has no authentication and must remain loopback-only.
