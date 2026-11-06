# Architecture

PeaCOBOL 0.2.0 separates deterministic analysis, data interpretation, execution, evidence, and audit concerns:

1. **Source assurance** discovers programs, calls, copy references, paragraphs, and deterministic findings without executing project code.
2. **Copybook layout** constructs a hierarchy, computes offsets and repeated lengths, and validates overlays.
3. **Record workbench** decodes display, binary, and packed-decimal fields and converts fixed records.
4. **Build adapter** invokes GnuCOBOL through a fixed argument array with a timeout; compiled programs are never run by PeaCOBOL.
5. **Evidence engine** hashes bounded project inputs and emits a reproducible manifest.
6. **Audit engine** appends hash-linked events for actions and outcomes.
7. **Local UI** is read-only, loopback-bound, and restricted to a configured project root.

Remote execution, credential handling, and mainframe submission remain outside this trust boundary.
