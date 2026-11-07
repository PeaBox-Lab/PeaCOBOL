from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
MAX_COVERAGE_BYTES = 10 * 1024 * 1024
SOURCE_SUFFIXES = {".cbl", ".cob"}
def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
def _read_json(path: Path, label: str) -> tuple[Path, bytes, dict[str, Any]]:
    if path.is_symlink():
        raise FileNotFoundError(f"{label} file not found: {path}")
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label} file not found: {path}")
    if path.stat().st_size > MAX_COVERAGE_BYTES:
        raise ValueError(f"{label} file exceeds {MAX_COVERAGE_BYTES} bytes")
    raw = path.read_bytes(); value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} input must be a JSON object")
    return path, raw, value
def _source_universe(project_root: Path, evidence: dict[str, Any]) -> set[tuple[str, int]]:
    source_hashes = evidence.get("source_hashes")
    if not isinstance(source_hashes, dict):
        raise ValueError("Evidence manifest requires source_hashes")
    universe: set[tuple[str, int]] = set()
    canonical_sources: set[str] = set()
    for relative, expected_hash in source_hashes.items():
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            raise ValueError("Evidence source hashes are invalid")
        if Path(relative).suffix.lower() not in SOURCE_SUFFIXES:
            continue
        candidate = project_root / relative
        current = project_root
        for part in Path(relative).parts:
            if part in ("", ".", ".."):
                raise ValueError("Evidence source path is invalid")
            current = current / part
            if current.is_symlink():
                raise ValueError("Evidence source path may not contain symlinks")
        candidate = candidate.resolve(); canonical = candidate.relative_to(project_root).as_posix()
        if canonical in canonical_sources:
            raise ValueError(f"Duplicate evidence source path: {canonical}")
        canonical_sources.add(canonical)
        if not candidate.is_file():
            raise FileNotFoundError(f"Evidence source file not found: {relative}")
        raw = candidate.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_hash:
            raise ValueError(f"Evidence source hash mismatch: {relative}")
        for number, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
            if len(line) >= 7 and line[6] in ("*", "/"):
                continue
            code = line[6:] if len(line) >= 7 and line[:6].strip().isdigit() else line
            if code.strip():
                universe.add((canonical, number))
    if not universe:
        raise ValueError("Evidence manifest contains no executable source lines")
    return universe
def import_coverage(path: Path, evidence_manifest: Path | None = None, project_root: Path | None = None) -> dict[str, Any]:
    path, raw, value = _read_json(path, "Coverage")
    lines = value.get("lines")
    if not isinstance(lines, list) or not lines or any(not isinstance(item, dict) for item in lines):
        raise ValueError("Coverage input requires a non-empty lines array")
    submitted: dict[tuple[str, int], int] = {}
    for item in lines:
        file = item.get("file"); line = item.get("line"); hits = item.get("hits")
        if not isinstance(file, str) or not file or not isinstance(line, int) or isinstance(line, bool) or line < 1 or not isinstance(hits, int) or isinstance(hits, bool) or hits < 0:
            raise ValueError("Each coverage line requires file, positive line, and nonnegative hits")
        key = (file.replace("\\", "/"), line)
        if key in submitted:
            raise ValueError(f"Duplicate coverage location: {key[0]}:{line}")
        submitted[key] = hits
    evidence_hash = None; verified = False
    if evidence_manifest is not None:
        if project_root is None:
            raise ValueError("Project root is required with an evidence manifest")
        evidence_path, _, evidence = _read_json(evidence_manifest, "Evidence")
        supplied = evidence.get("manifest_hash")
        if not isinstance(supplied, str):
            raise ValueError("Evidence manifest hash is missing")
        unsigned = dict(evidence); unsigned.pop("manifest_hash", None)
        calculated = hashlib.sha256(_canonical(unsigned)).hexdigest()
        if supplied != calculated:
            raise ValueError("Evidence manifest hash mismatch")
        project_root = project_root.resolve()
        if project_root.is_symlink() or not project_root.is_dir():
            raise NotADirectoryError("Project root is not a regular directory")
        universe = _source_universe(project_root, evidence)
        canonical_submitted: dict[tuple[str, int], int] = {}
        for (file, line), hits in submitted.items():
            raw_path = Path(file)
            if raw_path.is_absolute() or any(part in ("", ".", "..") for part in raw_path.parts):
                raise ValueError(f"Coverage location path is invalid: {file}")
            candidate = project_root / raw_path
            current = project_root
            for part in raw_path.parts:
                current = current / part
                if current.is_symlink():
                    raise ValueError("Coverage source path may not contain symlinks")
            canonical = candidate.resolve().relative_to(project_root).as_posix()
            key = (canonical, line)
            if key in canonical_submitted:
                raise ValueError(f"Duplicate canonical coverage location: {canonical}:{line}")
            canonical_submitted[key] = hits
        unknown = sorted(set(canonical_submitted) - universe)
        if unknown:
            raise ValueError(f"Coverage location is outside verified source: {unknown[0][0]}:{unknown[0][1]}")
        evidence_hash = supplied; verified = True
        normalized = [{"file": file, "line": line, "hits": canonical_submitted.get((file, line), 0)} for file, line in sorted(universe)]
    else:
        normalized = [{"file": file, "line": line, "hits": hits} for (file, line), hits in sorted(submitted.items())]
    total = len(normalized); covered = sum(item["hits"] > 0 for item in normalized)
    payload = {
        "schema": "peacobol-coverage-2",
        "source_file": path.name,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "evidence_manifest": evidence_manifest.name if evidence_manifest else None,
        "evidence_hash": evidence_hash,
        "evidence_verified": verified,
        "summary": {"lines": total, "covered": covered, "missed": total - covered, "percent": round(covered / total * 100, 2)},
        "lines": normalized,
    }
    payload["coverage_hash"] = hashlib.sha256(_canonical(payload)).hexdigest()
    return payload
