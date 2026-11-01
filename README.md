# PeaCOBOL 0.1.0

A local-first, user-friendly COBOL development and assurance toolkit. It does not send source or production data to AI services.

## Included MVP

- Project scaffolding and configuration
- Local browser dashboard
- COBOL program, paragraph, `CALL`, and `COPY` discovery
- Copybook layout inspection with offsets and storage sizes
- Initial deterministic assurance rules for unsafe control flow, unchecked arithmetic, external input, and I/O
- GnuCOBOL build adapter
- Banking and aerospace policy placeholders
- SHA-256 release evidence bundle
- Sample payment project, tests, CI, security model, roadmap

## Quick start

```bash
python -m pip install -e .
peacobol doctor
peacobol scan examples/payments
peacobol copybook examples/payments/copybooks/ACCOUNT.cpy
peacobol evidence examples/payments -o evidence.json
peacobol-ui
```

Open `http://127.0.0.1:8765`, enter the project path, and select **Analyze project**.

To compile, install GnuCOBOL and run:

```bash
peacobol build examples/payments
```

## Security position

PeaCOBOL binds the UI to loopback only, has no telemetry, requires no cloud service, executes no project source during analysis, and generates evidence with SHA-256 hashes. Version 0.1 is a development preview, not a certified banking or flight-safety tool.

## Supported targets

The analyzer is dialect-tolerant text analysis. Compilation in 0.1 targets GnuCOBOL. IBM Enterprise COBOL, JCL, Db2, CICS, MQ, z/OSMF and Zowe adapters are roadmap items and require access to their respective environments.
