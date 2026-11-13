# PeaCOBOL 1.2.0

PeaCOBOL is a local-first COBOL data, development, diagnostics, assurance, testing, and enterprise-inventory toolkit. Version 1.2.0 is the **Release Evidence Automation** release.

## Easy start

### Windows

Double-click:

```text
start.bat
```

The launcher finds Python 3.10+, starts the secure loopback GUI, and opens the one-time bootstrap page in your default browser. Keep the command window open; press `Ctrl+C` to stop.

### Linux

Run:

```bash
chmod +x start-linux.sh
./start-linux.sh
```

### Linux through Windows Subsystem for Linux

Double-click:

```text
start-linux.bat
```

This compatibility launcher invokes `start-linux.sh` through WSL. The launchers do not install packages, contact the internet, or modify the project.

## New enterprise foundations

- Db2 DDL-to-copybook compatibility checks with field-level reasons and gates
- Db2, CICS, and MQ resource inventories with source locations and integrity hashes
- Offline Zowe/zOSMF submission-plan validation using HTTPS allow-lists, RBAC roles, and `vault://` credential references
- CycloneDX-style offline SBOM with file hashes
- In-toto-style local attestations with optional strong HMAC-SHA256 signing through `PEACOBOL_ATTESTATION_KEY`
- Reproducible, content-addressed evidence archives
- Dry-run retention plans that never delete files
- Three new GUI workbenches: Enterprise resources, DB2 compatibility, and SBOM

## Enterprise CLI examples

Check a DB2 schema:

```bash
peacobol db2-check copybooks/ACCOUNT.cpy schema.sql --fail-on-incompatible -o db2-report.json
```

Inventory enterprise references:

```bash
peacobol resources . -o resource-inventory.json
```

Create a validated submission plan without submitting anything:

```bash
peacobol submission-plan . JOB.jcl \
  --system DEV \
  --allowlist config/submission-allowlist.json \
  --role developer \
  --credential-reference vault://mainframe/dev \
  -o submission-plan.json
```

The allow-list format is:

```json
{
  "systems": {
    "DEV": {
      "enabled": true,
      "url": "https://zos.example.com",
      "roles": ["developer", "release-manager"]
    }
  }
}
```

PeaCOBOL 1.2.0 only creates a **dry-run plan**. It does not perform a network request or submit a job.

Create supply-chain evidence:

```bash
peacobol sbom . -o sbom.json
peacobol attest PeaCOBOL-1.2.0.zip -o attestation.json
peacobol immutable-export reports/evidence.json sbom.json attestation.json -o evidence.tar.gz
peacobol retention-plan reports --days 90 -o retention-plan.json
```

For a keyed local attestation, set `PEACOBOL_ATTESTATION_KEY` to a secret of at least 32 bytes. The key is read from the environment and is never written to output.

## GUI

The loopback GUI exchanges a one-time launch token for an HttpOnly, SameSite session cookie and then removes the token from navigation URLs. It has ten workbenches:

1. Scan
2. Assurance
3. Diagnostics
4. Change impact
5. Test cases
6. Golden compare
7. Coverage
8. Enterprise resources
9. DB2 compatibility
10. SBOM

## Boundaries

This release does not connect to Db2, CICS, MQ, Zowe, or z/OSMF. Inventories and compatibility checks are static local analysis. Submission plans are validation-only. HMAC attestations provide shared-secret integrity, not public-key release signing. Production submission still requires an approved integration service, TLS trust, RBAC, a vault, independent review, and representative estate validation.
