# PeaCOBOL 0.5.0 Release Notes

## Release theme

**Assurance and Change Impact**

This release adds inspectable structural relationships and deterministic gates without claiming standards-complete parsing or semantic proof.

## Delivered

- Program call graph and copybook dependency graph.
- Field read/write inventory and paragraph-level control-flow edges.
- Supported external-input data-flow propagation.
- Rules `PC501` unbounded subscript review, `PC502` potential truncation, `PC503` external input at sensitive operations, and `PC504` `MOVE CORRESPONDING` change risk.
- Field-level copybook comparison with compatibility classification and a deterministic impact hash.
- SARIF 2.1.0 output.
- `assure` and `impact` CLI commands with exit-status gates.

## Validation summary

- 69 automated tests pass: 46 retained regression tests and 23 new 0.5.0 tests.
- Python source compilation passes.
- Tests cover resolved call and copybook edges, access and flow inventories, new findings, severity gates, compatible and breaking copybook changes, deterministic impact hashes, and SARIF mapping.
- End-to-end CLI validation covers JSON, SARIF, assurance gate, impact report, and breaking-change gate behavior.
- Review-driven fixes cover multi-target statements, qualified fields, conditional and computed control flow, non-downgradable profiles, build-output containment, and concurrent audit integrity.

## Boundary

The analyzer is intentionally heuristic and deterministic. Findings require review in context and are not proof that runtime failure or exploitation is possible.
