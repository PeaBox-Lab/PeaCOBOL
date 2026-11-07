from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .copybook import Field, parse_copybook, record_length


def _rows(nodes: list[Field], prefix: str = "") -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for node in nodes:
        path = f"{prefix}.{node.name}" if prefix else node.name
        rows[path] = {
            "path": path,
            "name": node.name,
            "parent": prefix or None,
            "level": node.level,
            "picture": node.picture,
            "usage": node.usage,
            "offset": node.offset,
            "length": node.length,
            "total_length": node.total_length,
            "occurs": node.occurs,
            "occurs_min": node.occurs_min,
            "redefines": node.redefines,
            "elementary": node.elementary,
        }
        rows.update(_rows(node.children, path))
    return rows


def compare_copybooks(before: Path, after: Path) -> dict[str, Any]:
    before = before.resolve()
    after = after.resolve()
    old_fields = parse_copybook(before)
    new_fields = parse_copybook(after)
    old = _rows(old_fields)
    new = _rows(new_fields)
    changes: list[dict[str, Any]] = []
    for path in sorted(old.keys() | new.keys()):
        if path not in old:
            changes.append({"path": path, "change": "added", "before": None, "after": new[path], "breaking": False})
            continue
        if path not in new:
            changes.append({"path": path, "change": "removed", "before": old[path], "after": None, "breaking": True})
            continue
        changed = [key for key in ("level", "picture", "usage", "offset", "length", "total_length", "occurs", "occurs_min", "redefines", "parent") if old[path][key] != new[path][key]]
        if changed:
            breaking = bool(set(changed) & {"picture", "usage", "offset", "length", "total_length", "occurs", "occurs_min", "redefines", "parent"})
            changes.append({"path": path, "change": "modified", "attributes": changed, "before": old[path], "after": new[path], "breaking": breaking})
    old_length = record_length(old_fields)
    new_length = record_length(new_fields)
    summary = {
        "added": sum(item["change"] == "added" for item in changes),
        "removed": sum(item["change"] == "removed" for item in changes),
        "modified": sum(item["change"] == "modified" for item in changes),
        "breaking": sum(bool(item["breaking"]) for item in changes),
    }
    payload = {
        "schema": "peacobol-copybook-impact-1",
        "before": {"file": before.name, "sha256": hashlib.sha256(before.read_bytes()).hexdigest(), "record_length": old_length},
        "after": {"file": after.name, "sha256": hashlib.sha256(after.read_bytes()).hexdigest(), "record_length": new_length},
        "record_length_delta": new_length - old_length,
        "changes": changes,
        "summary": summary,
        "compatible": summary["breaking"] == 0 and old_length == new_length,
    }
    payload["impact_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    return payload
