# PeaCOBOL 0.3.0

PeaCOBOL is a local-first COBOL data, development, and assurance toolkit. Version 0.3.0 is the **Build Profiles and IBM JCL** release.

## What is included

- Versioned `development`, `release`, `banking`, and `aerospace` profiles
- Project-level profile overrides with validation and safe built-in defaults
- Profile-driven text encoding, binary byte order, signed representation, compiler flags, and policy thresholds
- IBM Enterprise COBOL compile/link/run JCL generation with validated member and dataset names
- Normalized GnuCOBOL and IBM Enterprise COBOL diagnostics
- Reproducible build manifests with source and artifact SHA-256 hashes
- Policy gates for finding severity, build success, warnings, and evidence presence
- Hierarchical copybook parsing, `OCCURS`, `REDEFINES`, COMP-3, EBCDIC, record conversion, evidence manifests, and hash-chained action auditing from 0.2.0
- Safer GnuCOBOL compilation and a loopback-only local UI

## Quick start

```bash
python -m pip install -e .
peacobol doctor
peacobol profiles .
peacobol scan examples/payments
peacobol build examples/payments --profile development
```

Generate controlled IBM JCL without submitting it:

```bash
peacobol jcl examples/payments PAYMENT \
  --profile banking \
  --source-dataset BANK.COBOL.SOURCE \
  --copybook-dataset BANK.COBOL.COPY \
  --load-dataset BANK.COBOL.LOAD \
  -o PAYMENT.jcl
```

Evaluate a release gate:

```bash
peacobol gate examples/payments --profile release --with-build --with-evidence -o gate.json
```

A failed gate exits with status 3. Operational errors exit with status 2.

## Profile-driven data handling

```bash
peacobol decode layout.cpy record.dat --project . --profile banking
peacobol convert layout.cpy records.dat --project . --profile banking --format jsonl -o records.jsonl
```

An explicit `--encoding` overrides only the profile encoding; binary byte order and signedness still come from the selected profile.

## Profile overrides

`peacobol.json` may override selected built-in values while inheriting the remaining controls:

```json
{
  "default_profile": "release",
  "profiles": {
    "release": {
      "data": {"binary_byteorder": "little"},
      "policy": {"max_findings": {"medium": 0}}
    }
  }
}
```

## Security boundary

JCL is generated and validated locally; PeaCOBOL does not submit jobs or use credentials. GnuCOBOL compilation uses fixed argument arrays with `shell=False`, timeouts, bounded diagnostics, and collision-free targets. Build execution is local and is not a sandbox.
