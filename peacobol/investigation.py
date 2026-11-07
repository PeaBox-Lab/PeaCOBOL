from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
from .knowledge import lookup
from .spool import parse_spool, read_spool
MAX_CONTEXT_LINES = 8
MAX_SOURCE_BYTES = 5 * 1024 * 1024
def _safe_source(root: Path, raw: str) -> Path | None:
    unresolved = root / raw
    try:
        relative = unresolved.relative_to(root)
    except ValueError:
        return None
    current = root
    for part in relative.parts:
        if part in ("", ".", ".."):
            return None
        current = current / part
        if current.is_symlink():
            return None
    candidate = unresolved.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if candidate.suffix.lower() not in {".cbl", ".cob", ".cpy"} or not candidate.is_file() or candidate.stat().st_size > MAX_SOURCE_BYTES:
        return None
    return candidate
def _context(root: Path, reference: dict[str, Any], radius: int) -> dict[str, Any]:
    path = _safe_source(root, reference["file"])
    if path is None:
        return {**reference, "available": False}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    target = reference["line"]
    start = max(1, target - radius)
    end = min(len(lines), target + radius)
    return {
        **reference,
        "available": True,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "context_start": start,
        "context_end": end,
        "context": [{"line": number, "text": lines[number - 1]} for number in range(start, end + 1)],
    }
def _checklist(report: dict[str, Any], knowledge: list[dict[str, Any]], correlated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = [
        {"order": 1, "action": "Preserve the original spool and record its SHA-256 hash.", "reason": "Maintains repeatable evidence for the investigation."},
        {"order": 2, "action": "Confirm the failing job step and highest return code.", "reason": "Separates compile, link, and runtime failures."},
    ]
    if report["abends"]:
        items.append({"order": len(items) + 1, "action": "Review each detected abnormal-termination entry and its bounded spool context.", "reason": "The termination marker is the primary runtime failure signal."})
    if report["file_statuses"]:
        items.append({"order": len(items) + 1, "action": "Trace each detected file-status value to its file operation and approved catalog entry.", "reason": "File failures require operation and environment context."})
    if report["compiler_diagnostics"]:
        items.append({"order": len(items) + 1, "action": "Resolve normalized compiler errors before warnings and notes.", "reason": "Compiler severity provides a deterministic investigation order."})
    if correlated:
        items.append({"order": len(items) + 1, "action": "Review the correlated source excerpts and verify source hashes against the failing build.", "reason": "Prevents remediation against a different source revision."})
    for entry in knowledge:
        for check in entry["checks"]:
            items.append({"order": len(items) + 1, "action": check, "reason": f"Catalog guidance for {entry['kind']} {entry['code']}."})
    items.append({"order": len(items) + 1, "action": "Reproduce under the same profile and compare the new evidence bundle.", "reason": "Confirms that the remediation changed the observed failure deterministically."})
    return items
def diagnose(root: Path, spool_text: str, context_lines: int = 3) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Project directory not found: {root}")
    if context_lines < 0 or context_lines > MAX_CONTEXT_LINES:
        raise ValueError(f"Context lines must be between 0 and {MAX_CONTEXT_LINES}")
    report = parse_spool(spool_text)
    knowledge = [lookup(root, "abend", item["code"]) for item in report["abends"]]
    knowledge.extend(lookup(root, "file-status", item["code"]) for item in report["file_statuses"])
    references = list(report["source_references"])
    for diagnostic in report["compiler_diagnostics"]:
        if diagnostic.get("file") and diagnostic.get("line"):
            references.append({"file": diagnostic["file"], "line": diagnostic["line"], "spool_line": None})
    unique: dict[tuple[str, int], dict[str, Any]] = {}
    for reference in references:
        unique[(reference["file"], reference["line"])] = reference
    correlated = [_context(root, reference, context_lines) for reference in unique.values()]
    return {
        "schema": "peacobol-diagnosis-1",
        "project": root.name,
        "spool": report,
        "knowledge": knowledge,
        "source_context": correlated,
        "checklist": _checklist(report, knowledge, correlated),
        "ok": report["ok"],
    }
def failure_bundle(root: Path, spool_path: Path, output_hint: str | None = None, context_lines: int = 3) -> dict[str, Any]:
    root = root.resolve()
    spool_bytes, spool_text = read_spool(spool_path)
    spool_path = spool_path.resolve()
    diagnosis = diagnose(root, spool_text, context_lines)
    payload = {
        "schema": "peacobol-failure-bundle-1",
        "project": root.name,
        "spool_file": spool_path.name,
        "spool_sha256": hashlib.sha256(spool_bytes).hexdigest(),
        "output_hint": output_hint,
        "diagnosis": diagnosis,
    }
    payload["bundle_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    return payload
