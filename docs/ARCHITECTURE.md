# Architecture

PeaCOBOL 0.3.0 separates deterministic analysis, data interpretation, controlled build generation, execution, policy, evidence, and audit concerns:

1. **Source assurance** discovers programs, calls, copy references, paragraphs, and deterministic findings without executing project code.
2. **Copybook layout** constructs a hierarchy, computes offsets and repeated lengths, and validates overlays.
3. **Record workbench** decodes display, binary, and packed-decimal fields using profile-selected encoding and binary representation.
4. **Profile engine** merges validated built-in profiles with project-local overrides.
5. **Build adapter** invokes GnuCOBOL through a fixed argument array with a timeout and emits normalized diagnostics plus a hashed manifest.
6. **JCL generator** emits IBM Enterprise COBOL compile/link/run JCL but never submits it.
7. **Policy engine** evaluates explicit finding, warning, build, and evidence requirements.
8. **Evidence and audit engines** create reproducible manifests and hash-linked action records.
9. **Local UI** is read-only, loopback-bound, and restricted to a configured project root.

Remote execution, credential handling, and mainframe submission remain outside this trust boundary.
