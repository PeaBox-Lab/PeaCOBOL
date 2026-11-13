# Architecture

PeaCOBOL 1.3.0 adds release-evidence alignment across package metadata, runtime version, GUI, loopback server, launchers, and automated tests. The offline enterprise and supply-chain layer from 1.2.0 is retained:

1. **Db2 compatibility engine** compares local DDL columns with computed COBOL field representation.
2. **Resource inventory engine** extracts Db2 object references, CICS commands/resources, and MQ API calls with locations.
3. **Submission-plan validator** verifies a local HTTPS allow-list, target enablement, role membership, vault credential reference, JCL containment, and hashes—but has no network client.
4. **SBOM engine** inventories bounded project files and hashes their contents.
5. **Attestation engine** creates in-toto-style statements and optionally applies strong environment-provided HMAC integrity.
6. **Immutable-export engine** creates reproducible content-addressed archives with normalized metadata.
7. **Retention planner** identifies age-based candidates without deleting anything.
8. **GUI presentation layer** exposes enterprise inventory, DB2 checks, and SBOM alongside the existing seven workbenches.
9. **Launcher layer** starts the existing token-protected loopback GUI without installing dependencies.

Remote submission, credential retrieval, and public-key signing remain outside this trust boundary.
