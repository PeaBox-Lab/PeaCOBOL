"""Rules integrity for PeaCOBOL release hardening (1.2.0).

Every analysis report embeds a hash of the rule-definition sources so a
tampered analyzer on disk is detectable by comparing a report's embedded
manifest against a freshly computed one. The manifest is reproducible:
same files, same hash.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

RULE_SOURCES = ("peacobol.core", "peacobol.assurance")
MANIFEST_SCHEMA = "peacobol-rules-manifest-1"


def _module_path(module_name: str) -> Path | None:
    spec = importlib.util.find_spec(module_name)
    if spec is None or not spec.origin:
        return None
    return Path(spec.origin).resolve()


def rules_manifest() -> dict[str, Any]:
    """Compute a deterministic manifest of rule-definition sources."""
    modules: dict[str, dict[str, str]] = {}
    for module_name in RULE_SOURCES:
        path = _module_path(module_name)
        if path is None or not path.is_file():
            raise FileNotFoundError(f"Rule source module not found: {module_name}")
        data = path.read_bytes()
        modules[module_name] = {
            "file": path.name,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }
    manifest: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA,
        "rule_sources": dict(sorted(modules.items())),
    }
    manifest["manifest_hash"] = hashlib.sha256(
        json.dumps(
            {"schema": manifest["schema"], "rule_sources": manifest["rule_sources"]},
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return manifest


def verify_rules_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Recompute the current manifest and compare it against an embedded one."""
    try:
        current = rules_manifest()
    except FileNotFoundError as exc:
        return {"ok": False, "error": str(exc)}
    embedded_hash = manifest.get("manifest_hash") if isinstance(manifest, dict) else None
    if not embedded_hash:
        return {"ok": False, "error": "Manifest is missing a manifest_hash"}
    return {"ok": bool(embedded_hash == current["manifest_hash"]),
            "embedded": embedded_hash, "current": current["manifest_hash"]}
