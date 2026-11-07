from __future__ import annotations

import hashlib
import gzip
import hmac
import json
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import _safe_files


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sbom(root: Path) -> dict[str, Any]:
    root = root.resolve()
    pyproject = root / "pyproject.toml"
    files = []
    for path in _safe_files(root):
        rel = path.relative_to(root).as_posix()
        files.append({"path": rel, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    components = [{"type": "file", "name": item["path"], "version": "sha256:" + item["sha256"], "hashes": [{"alg": "SHA-256", "content": item["sha256"]}], "properties": [{"name": "peacobol:bytes", "value": str(item["bytes"])}]} for item in files]
    serial = hashlib.sha256(root.name.encode()).hexdigest()[:32]
    serial = f"{serial[:8]}-{serial[8:12]}-{serial[12:16]}-{serial[16:20]}-{serial[20:32]}"
    payload = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": "urn:uuid:" + serial,
        "version": 1,
        "metadata": {"component": {"type": "application", "name": "peacobol", "version": _version(pyproject)}, "properties": [{"name": "peacobol:file-count", "value": str(len(files))}]},
        "components": components,
    }
    payload["bom_hash"] = hashlib.sha256(_canonical(payload)).hexdigest()
    return payload


def _version(pyproject: Path) -> str:
    if not pyproject.exists():
        return "unknown"
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("version") and "=" in line:
            return line.split("=", 1)[1].strip().strip('"')
    return "unknown"


def attest(subject: Path, predicate_type: str = "https://slsa.dev/provenance/v1") -> dict[str, Any]:
    subject = subject.resolve()
    if subject.is_symlink() or not subject.is_file():
        raise FileNotFoundError(f"Attestation subject not found: {subject}")
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": subject.name, "digest": {"sha256": hashlib.sha256(subject.read_bytes()).hexdigest()}}],
        "predicateType": predicate_type,
        "predicate": {"builder": {"id": "peacobol-local"}, "buildType": "peacobol/offline", "invocation": {"networkAccess": False}},
    }
    key = os.environ.get("PEACOBOL_ATTESTATION_KEY")
    envelope = {"schema": "peacobol-attestation-1", "statement": statement, "signature": None, "signature_algorithm": None}
    if key:
        if len(key.encode("utf-8")) < 32:
            raise ValueError("PEACOBOL_ATTESTATION_KEY must contain at least 32 bytes")
        envelope["signature"] = hmac.new(key.encode("utf-8"), _canonical(statement), hashlib.sha256).hexdigest()
        envelope["signature_algorithm"] = "HMAC-SHA256"
    envelope["attestation_hash"] = hashlib.sha256(_canonical(envelope)).hexdigest()
    return envelope


def verify_attestation(envelope: dict[str, Any]) -> dict[str, Any]:
    signature = envelope.get("signature"); algorithm = envelope.get("signature_algorithm"); key = os.environ.get("PEACOBOL_ATTESTATION_KEY")
    if not signature:
        return {"ok": False, "signed": False, "error": "Attestation is unsigned"}
    if algorithm != "HMAC-SHA256" or not key or len(key.encode("utf-8")) < 32:
        return {"ok": False, "signed": True, "error": "Matching strong HMAC verification key is unavailable"}
    expected = hmac.new(key.encode("utf-8"), _canonical(envelope["statement"]), hashlib.sha256).hexdigest()
    return {"ok": hmac.compare_digest(signature, expected), "signed": True, "algorithm": algorithm}


def immutable_export(files: list[Path], output: Path) -> dict[str, Any]:
    if not files:
        raise ValueError("At least one evidence file is required")
    output = Path(os.path.abspath(os.fspath(output)))
    resolved = []
    names: set[str] = set()
    for path in files:
        if path.is_symlink() or not path.resolve().is_file():
            raise FileNotFoundError(f"Evidence file not found: {path}")
        path = path.resolve()
        if path.name in names:
            raise ValueError(f"Duplicate evidence filename: {path.name}")
        names.add(path.name); resolved.append(path)
    manifest = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(resolved, key=lambda item: item.name)}
    export_id = hashlib.sha256(_canonical(manifest)).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(descriptor, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w") as archive:
                    for path in sorted(resolved, key=lambda item: item.name):
                        info = archive.gettarinfo(str(path), arcname=f"evidence/{path.name}")
                        info.mtime = 0; info.uid = 0; info.gid = 0; info.uname = ""; info.gname = ""; info.mode = 0o600
                        with path.open("rb") as handle:
                            archive.addfile(info, handle)
                    manifest_bytes = (json.dumps({"export_id": export_id, "files": manifest}, sort_keys=True, indent=2) + "\n").encode("utf-8")
                    info = tarfile.TarInfo("manifest.json"); info.size = len(manifest_bytes); info.mtime = 0; info.uid = 0; info.gid = 0; info.mode = 0o600
                    import io
                    archive.addfile(info, io.BytesIO(manifest_bytes))
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {"schema": "peacobol-immutable-export-1", "output": output.name, "export_id": export_id, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "files": manifest}


def retention_plan(directory: Path, days: int, now: datetime | None = None) -> dict[str, Any]:
    directory = directory.resolve()
    if days < 1:
        raise ValueError("Retention days must be positive")
    if not directory.is_dir():
        raise NotADirectoryError("Retention directory not found")
    current = now or datetime.now(timezone.utc)
    candidates = []
    for path in sorted(directory.iterdir()):
        if path.is_symlink() or not path.is_file():
            continue
        age = (current - datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)).days
        if age >= days:
            candidates.append({"file": path.name, "age_days": age, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return {"schema": "peacobol-retention-plan-1", "mode": "dry-run-only", "retention_days": days, "candidates": candidates, "notice": "No files were deleted."}
