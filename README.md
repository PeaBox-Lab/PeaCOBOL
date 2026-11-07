# PeaCOBOL 0.5.0

PeaCOBOL is a local-first COBOL data, development, diagnostics, assurance, and change-impact toolkit. Version 0.5.0 is the **Assurance and Change Impact** release.

## What is included

- Program call graphs with resolved and unresolved targets
- Program and copybook dependency graphs, including nested `COPY` references
- Field read/write inventories for deterministic statement patterns
- Paragraph-level control-flow edges for fallthrough, `PERFORM`, and `GO TO`
- External-input data-flow tracking through supported `MOVE` and `COMPUTE` patterns
- Assurance rules for unbounded subscripts, potentially truncating moves, sensitive use of external input, and `MOVE CORRESPONDING` change risk
- Field-level copybook change-impact comparison with source hashes, record-length deltas, compatibility decisions, and an overall impact hash
- SARIF 2.1.0 export and configurable severity gates
- Diagnostics Center, build profiles, IBM JCL generation, record tools, reproducible evidence, and hash-chained auditing from earlier releases

## Quick start

```bash
python -m pip install -e .
peacobol assure examples/payments -o assurance.json
peacobol assure examples/payments --format sarif -o assurance.sarif
peacobol assure examples/payments --fail-on high -o gate.json
```

A failed assurance gate exits with status 3. Thresholds include the selected severity and all more severe findings.

Compare copybook versions:

```bash
peacobol impact before/ACCOUNT.cpy after/ACCOUNT.cpy -o impact.json
peacobol impact before/ACCOUNT.cpy after/ACCOUNT.cpy --fail-on-breaking -o impact-gate.json
```

`--fail-on-breaking` exits with status 3 when a field is removed or when its storage, location, occurrence, overlay, usage, picture, or parent changes. Record-length changes are also incompatible.

## Assurance outputs

The JSON assurance report contains:

- `program_graph`
- `copybook_graph`
- `field_access`
- `control_flow`
- `data_flow`
- `findings`
- `summary`
- `gate`

SARIF output contains one rule definition per PeaCOBOL rule and a result with file, line, severity, message, and remediation for every finding.

## Boundaries

The analyzer remains deterministic and narrower than a compiler. Access and flow inventories cover explicit supported statement patterns and do not claim complete COBOL semantic analysis. A finding identifies a review requirement, not proof of a defect. Change-impact comparison is structural and does not replace application or interface testing.
