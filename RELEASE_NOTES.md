# PeaCOBOL 0.2.0 Release Notes

## Release theme

**Data Integrity and Audit Workbench**

This release advances the supplied working 0.1.0 application to 0.2.0. It prioritizes correct copybook storage, controlled record conversion, reproducible evidence, and traceable actions before mainframe submission or enterprise integrations are introduced.

## Validation summary

- 16 automated tests passed.
- Python source compilation passed.
- Sample scan returned 2 high, 1 medium, and 1 low finding.
- ACCOUNT copybook calculated a 19-byte record.
- COMP-3 sample decoded to `1234567.89`.
- Two fixed records converted successfully to JSONL.
- Repeated evidence generation produced identical output.
- Audit hash-chain verification passed.
- Missing GnuCOBOL was handled as a clear capability limitation; no alternate or shell-based compilation was attempted.

## Review first

Read `docs/AUDIT_REPORT.md` for the full application/process audit and `ROADMAP.md` for the prioritized release sequence.
