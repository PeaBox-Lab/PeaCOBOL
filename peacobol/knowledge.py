from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CODE_RE = re.compile(r"^[A-Z0-9-]{1,32}$")

BUILTIN_CATALOGS: dict[str, dict[str, dict[str, Any]]] = {
    "abend": {
        "UNKNOWN": {
            "title": "Unclassified abnormal termination",
            "summary": "An abnormal termination marker was detected but no site-specific catalog entry matched it.",
            "checks": ["Confirm the exact termination code and failing step.", "Review the bounded spool context and correlated source lines.", "Consult the approved platform runbook for the detected code."],
        }
    },
    "file-status": {
        "UNKNOWN": {
            "title": "Unclassified COBOL file status",
            "summary": "A file-status value was detected but no site-specific catalog entry matched it.",
            "checks": ["Confirm the two-character status and the affected file operation.", "Review SELECT, FD, assignment, organization, and access-mode settings.", "Consult the approved application or platform runbook for the detected status."],
        }
    },
}


def _validate_entry(kind: str, code: str, value: Any) -> dict[str, Any]:
    code = code.upper()
    if not CODE_RE.fullmatch(code):
        raise ValueError(f"Invalid {kind} knowledge code: {code}")
    if not isinstance(value, dict):
        raise ValueError(f"Knowledge entry {kind}:{code} must be an object")
    title = value.get("title")
    summary = value.get("summary")
    checks = value.get("checks")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"Knowledge entry {kind}:{code} requires a title")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError(f"Knowledge entry {kind}:{code} requires a summary")
    if not isinstance(checks, list) or not checks or any(not isinstance(item, str) or not item.strip() for item in checks):
        raise ValueError(f"Knowledge entry {kind}:{code} requires non-empty checks")
    return {"title": title.strip(), "summary": summary.strip(), "checks": [item.strip() for item in checks]}


def load_catalog(root: Path | None = None, kind: str = "abend") -> dict[str, dict[str, Any]]:
    if kind not in BUILTIN_CATALOGS:
        raise ValueError(f"Unknown knowledge catalog: {kind}")
    catalog = {code: dict(value) for code, value in BUILTIN_CATALOGS[kind].items()}
    if root is not None:
        path = root.resolve() / ".peacobol" / "knowledge" / f"{kind}.json"
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError(f"Knowledge catalog must be an object: {path}")
            for code, value in raw.items():
                catalog[code.upper()] = _validate_entry(kind, code, value)
    return {code: _validate_entry(kind, code, value) for code, value in sorted(catalog.items())}


def lookup(root: Path | None, kind: str, code: str) -> dict[str, Any]:
    code = code.upper()
    catalog = load_catalog(root, kind)
    matched = code in catalog
    entry = catalog.get(code, catalog["UNKNOWN"])
    return {"schema": "peacobol-knowledge-1", "kind": kind, "code": code, "matched": matched, **entry}


def list_knowledge(root: Path | None = None) -> dict[str, Any]:
    return {
        "schema": "peacobol-knowledge-list-1",
        "catalogs": {kind: load_catalog(root, kind) for kind in BUILTIN_CATALOGS},
    }
