# PeaCOBOL 0.2.0

PeaCOBOL is a local-first COBOL data, development, and assurance toolkit. Version 0.2.0 is the **Data Integrity and Audit Workbench** release, built from an audit of the supplied 0.1.0 implementation.

## What is included

- Hierarchical copybook parsing with nested groups
- `OCCURS` sizing and repeated-field decoding
- `REDEFINES` overlay offsets and validation
- DISPLAY, BINARY, and COMP-3 storage calculations
- COMP-3 encode/decode with invalid-nibble checks
- ASCII, UTF-8, EBCDIC CP037, and EBCDIC CP500 record decoding
- Fixed-record conversion to JSONL and flat CSV
- Bounded hex inspection
- Deterministic source scanning and assurance findings
- Reproducible evidence manifests that exclude generated and audit content
- Hash-chained, append-only local action audit records
- Safer GnuCOBOL compilation with fixed argument arrays, timeouts, bounded diagnostics, copybook include paths, and collision-free targets
- A loopback-only UI constrained to an administrator-selected root

## Quick start

```bash
python -m pip install -e .
peacobol doctor
peacobol scan examples/payments
peacobol copybook examples/payments/copybooks/ACCOUNT.cpy
peacobol evidence examples/payments -o examples/payments/reports/evidence.json
```

Data commands:

```bash
peacobol decode layout.cpy record.dat --encoding cp037
peacobol convert layout.cpy records.dat --encoding cp037 --format jsonl -o records.jsonl
peacobol hex records.dat --limit 4096
```

Audit commands:

```bash
peacobol scan examples/payments
peacobol audit-verify examples/payments/.peacobol/audit.jsonl
```

All CLI actions write a local hash-chained event by default. Use `--audit-log` to select another path or `--no-audit` for an intentionally unaudited invocation.

## UI

```bash
peacobol-ui --root /path/to/approved/projects
```

The UI binds to `127.0.0.1` and rejects project paths outside the configured root.

## Current boundaries

The parser is deterministic and intentionally narrower than a full COBOL compiler. It does not yet implement condition names, RENAMES, variable-length OCCURS DEPENDING ON decoding, every national/edited picture clause, source-format directives, or dialect-specific preprocessing. Compilation targets GnuCOBOL when `cobc` is installed. No remote job submission is included.
