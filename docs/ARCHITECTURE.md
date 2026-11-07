# Architecture

PeaCOBOL 0.5.0 separates deterministic source interpretation into inspectable layers:

1. **Source inventory** applies bounded file discovery and comment-aware line extraction.
2. **Base assurance** identifies programs, calls, copy references, paragraphs, and stable line-oriented findings.
3. **Graph engine** resolves program identities, call targets, copybook names, and paragraph edges.
4. **Access and flow engine** records supported field reads, writes, and external-input propagation.
5. **Change-impact engine** compares flattened copybook paths and storage attributes, then hashes the canonical result.
6. **SARIF adapter** maps rules, severities, locations, and remediation into SARIF 2.1.0.
7. **Gate engine** applies selected severity or breaking-change thresholds with automation-safe exit status 3.
8. **Diagnostics, build, data, evidence, and audit layers** retain the controls delivered in earlier releases.

The architecture deliberately avoids claiming complete compiler semantics. Each derived relationship retains its file and line evidence where available.
