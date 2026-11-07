# PeaCOBOL 0.4.0

PeaCOBOL is a local-first COBOL data, development, assurance, and diagnostics toolkit. Version 0.4.0 is the **Diagnostics Center** release.

## What is included

- Deterministic spool parsing for job steps, return codes, abnormal-termination markers, COBOL file-status values, compiler diagnostics, and source references
- Extensible ABEND and file-status knowledge catalogs under `.peacobol/knowledge/`
- Explicit fallback guidance when a site catalog has no matching code
- Compiler and spool correlation with bounded source excerpts and source SHA-256 hashes
- Repeatable failure bundles containing spool hashes, diagnosis data, source context, remediation checklists, and an overall bundle hash
- Versioned build profiles, IBM compile/link/run JCL generation, normalized compiler diagnostics, build manifests, and policy gates from 0.3.0
- Copybook analysis, record conversion, evidence manifests, and hash-chained action auditing from earlier releases

## Quick start

```bash
python -m pip install -e .
peacobol doctor
peacobol diagnose examples/payments failure.log -o diagnosis.json
peacobol failure-bundle examples/payments failure.log -o failure-bundle.json
```

Inspect the diagnostic catalogs:

```bash
peacobol knowledge examples/payments
peacobol knowledge examples/payments --kind abend --code S0C7
peacobol knowledge examples/payments --kind file-status --code 35
```

## Site-specific knowledge

PeaCOBOL does not claim environment-specific meanings without an approved local catalog. Add validated JSON entries at:

- `.peacobol/knowledge/abend.json`
- `.peacobol/knowledge/file-status.json`

Example structure:

```json
{
  "SITE-CODE": {
    "title": "Approved site title",
    "summary": "Approved site explanation.",
    "checks": ["Follow the approved local runbook."]
  }
}
```

Catalog codes, titles, summaries, and checklist items are validated before use.

## Failure-bundle integrity

A bundle records the original spool filename and SHA-256, bounded correlated source excerpts with source hashes, normalized evidence, an ordered checklist, and a deterministic `bundle_hash`. The bundle contains no submission, credential, or remote-execution behavior.

## Boundaries

The spool parser is deterministic and intentionally supports bounded common marker formats rather than every vendor message. Site-specific facts belong in approved local catalogs. Source correlation reads only regular, non-symlinked files beneath the selected project root. Spool files are size-limited and symlinks are rejected.
