# Architecture

PeaCOBOL separates deterministic analysis from execution:

1. **Parser and index** reads source and copybooks without executing them.
2. **Assurance engine** runs versioned deterministic rules.
3. **Build adapter** invokes GnuCOBOL only when explicitly requested.
4. **Evidence engine** records hashes, environment, findings, and results.
5. **Local UI** binds to `127.0.0.1` and exposes read-only analysis.

Planned adapters: IBM Enterprise COBOL/JCL, Zowe CLI/zOSMF, Db2 bind, CICS, MQ, COBOL Check, SARIF, SBOM, signed attestations and organization policy packs.
