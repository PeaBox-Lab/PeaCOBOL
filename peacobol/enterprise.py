from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .copybook import flatten_fields, parse_copybook, picture_digits
from .core import _safe_files

DB2_TYPE_RE = re.compile(r"\b(CREATE\s+TABLE|ALTER\s+TABLE)\s+([A-Z0-9_.\"]+)", re.I)
COLUMN_RE = re.compile(r"(?:\(|,)\s*([A-Z][A-Z0-9_#$@]*)\s+(CHAR|VARCHAR|SMALLINT|INTEGER|BIGINT|DECIMAL|NUMERIC|DATE|TIME|TIMESTAMP)(?:\s*\(\s*(\d+)(?:\s*,\s*(\d+))?\s*\))?", re.I)
EXEC_SQL_RE = re.compile(r"\bEXEC\s+SQL\b", re.I)
DB2_OBJECT_RE = re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE|DELETE\s+FROM)\s+([A-Z0-9_.]+)", re.I)
CICS_RE = re.compile(r"\bEXEC\s+CICS\s+([A-Z][A-Z0-9-]*)(.*?)(?:END-EXEC|$)", re.I)
CICS_RESOURCE_RE = re.compile(r"\b(FILE|QUEUE|PROGRAM|TRANSID|MAP|MAPSET)\s*\(\s*([^\s)]+)", re.I)
MQ_RE = re.compile(r"\b(MQOPEN|MQGET|MQPUT1?|MQCLOSE|MQCONN|MQDISC)\b", re.I)
STRING_RE = re.compile(r"['\"]([^'\"]+)['\"]")


def _sql_columns(text: str) -> list[dict[str, Any]]:
    normalized = re.sub(r"--[^\n]*", " ", text)
    normalized = re.sub(r"\s+", " ", normalized)
    columns = []
    for match in COLUMN_RE.finditer(normalized):
        db2_type = match.group(2).upper()
        length = int(match.group(3)) if match.group(3) else None
        scale = int(match.group(4)) if match.group(4) else None
        if db2_type in {"CHAR", "VARCHAR", "DECIMAL", "NUMERIC"} and length is None:
            raise ValueError(f"DB2 {db2_type} column {match.group(1)} requires parsed parameters")
        columns.append({"name": match.group(1).upper(), "type": db2_type, "length": length, "scale": scale})
    return columns


def _compatible(field: dict[str, Any], column: dict[str, Any]) -> tuple[bool, str]:
    picture = (field.get("picture") or "").upper(); usage = field.get("usage", "DISPLAY").upper(); db2 = column["type"]
    alphanumeric = "X" in picture or "A" in picture
    numeric = "9" in picture and not alphanumeric
    if db2 in {"CHAR", "VARCHAR", "DATE", "TIME", "TIMESTAMP"}:
        if not alphanumeric:
            return False, "DB2 character or temporal column maps to a non-alphanumeric COBOL field"
        if column.get("length") and field["length"] < column["length"]:
            return False, "COBOL field is shorter than the DB2 column"
        return True, "compatible character storage"
    if db2 in {"SMALLINT", "INTEGER", "BIGINT"}:
        if not numeric:
            return False, "DB2 integer maps to a nonnumeric COBOL field"
        if usage not in {"COMP", "COMP-4", "COMP-5", "BINARY", "DISPLAY"}:
            return False, "COBOL usage is not an integer-compatible representation"
        return True, "compatible integer representation"
    if db2 in {"DECIMAL", "NUMERIC"}:
        if not numeric:
            return False, "DB2 decimal maps to a nonnumeric COBOL field"
        digits = picture_digits(picture)
        cobol_scale = picture_digits(picture.split("V", 1)[1]) if "V" in picture else 0
        db2_precision = column.get("length") or 0
        db2_scale = column.get("scale") or 0
        if digits < db2_precision:
            return False, "COBOL picture has fewer digits than the DB2 precision"
        if cobol_scale != db2_scale:
            return False, "COBOL implied decimal scale does not match the DB2 scale"
        if digits - cobol_scale < db2_precision - db2_scale:
            return False, "COBOL picture has insufficient integer digits for the DB2 column"
        return True, "compatible decimal representation"
    return False, "unsupported DB2 type"


def db2_compatibility(copybook: Path, ddl: Path) -> dict[str, Any]:
    copybook = copybook.resolve(); ddl = ddl.resolve()
    fields = {field.name: field.to_dict() for field in flatten_fields(parse_copybook(copybook)) if field.elementary}
    ddl_text = ddl.read_text(encoding="utf-8", errors="replace")
    columns = _sql_columns(ddl_text)
    results = []
    for column in columns:
        field = fields.get(column["name"].replace("_", "-")) or fields.get(column["name"])
        if field is None:
            results.append({"column": column, "field": None, "compatible": False, "reason": "No same-name COBOL field was found"})
        else:
            compatible, reason = _compatible(field, column)
            results.append({"column": column, "field": field, "compatible": compatible, "reason": reason})
    payload = {
        "schema": "peacobol-db2-compatibility-1",
        "copybook": {"file": copybook.name, "sha256": hashlib.sha256(copybook.read_bytes()).hexdigest()},
        "ddl": {"file": ddl.name, "sha256": hashlib.sha256(ddl.read_bytes()).hexdigest()},
        "tables": [match.group(2).strip('"').upper() for match in DB2_TYPE_RE.finditer(ddl_text)],
        "results": results,
        "summary": {"columns": len(results), "compatible": sum(item["compatible"] for item in results), "incompatible": sum(not item["compatible"] for item in results)},
    }
    payload["ok"] = payload["summary"]["incompatible"] == 0
    payload["manifest_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    return payload


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def resource_inventory(root: Path) -> dict[str, Any]:
    root = root.resolve(); db2 = []; cics = []; mq = []
    for path in _safe_files(root, {".cbl", ".cob"}):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        cleaned = "\n".join("" if len(line) >= 7 and line[6] in ("*", "/") else line for line in text.splitlines())
        for block in re.finditer(r"\bEXEC\s+SQL\b(.*?)\bEND-EXEC\b", cleaned, re.I | re.S):
            for name in DB2_OBJECT_RE.findall(block.group(1)):
                db2.append({"file": rel, "line": _line_number(cleaned, block.start()), "object": name.upper(), "operation": "SQL"})
        for block in re.finditer(r"\bEXEC\s+CICS\s+([A-Z][A-Z0-9-]*)(.*?)\bEND-EXEC\b", cleaned, re.I | re.S):
            command, tail = block.groups(); resources = [{"type": kind.upper(), "name": value.strip("'\"").upper()} for kind, value in CICS_RESOURCE_RE.findall(tail)]
            cics.append({"file": rel, "line": _line_number(cleaned, block.start()), "command": command.upper(), "resources": resources})
        for match in MQ_RE.finditer(cleaned):
            snippet = cleaned[match.start():match.start()+500]
            strings = STRING_RE.findall(snippet)
            mq.append({"file": rel, "line": _line_number(cleaned, match.start()), "operation": match.group(1).upper(), "literals": strings[:4]})
    payload = {"schema": "peacobol-resource-inventory-1", "project": root.name, "db2": db2, "cics": cics, "mq": mq, "summary": {"db2": len(db2), "cics": len(cics), "mq": len(mq)}}
    payload["inventory_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    return payload


def submission_plan(root: Path, jcl: Path, system: str, allowlist: Path, role: str, credential_reference: str) -> dict[str, Any]:
    root = root.resolve(); jcl = jcl.resolve(); allowlist = allowlist.resolve()
    if jcl.is_symlink() or not jcl.is_file():
        raise FileNotFoundError("JCL file was not found")
    jcl.relative_to(root)
    config = json.loads(allowlist.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("systems"), dict):
        raise ValueError("Allow-list requires a systems object")
    entry = config["systems"].get(system)
    if not isinstance(entry, dict) or entry.get("enabled") is not True:
        raise ValueError("Target system is not explicitly enabled")
    if role not in entry.get("roles", []):
        raise PermissionError("Role is not allowed for the target system")
    if not credential_reference.startswith("vault://"):
        raise ValueError("Credentials must be referenced through vault:// and are never stored")
    url = entry.get("url")
    if not isinstance(url, str) or any(char.isspace() for char in url):
        raise ValueError("Target system requires a valid HTTPS URL")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Target URL must be HTTPS without credentials, query, or fragment")
    url = parsed.geturl()
    payload = {
        "schema": "peacobol-submission-plan-1",
        "mode": "dry-run-only",
        "system": system,
        "url": url,
        "role": role,
        "credential_reference": credential_reference,
        "tls_verify": True,
        "jcl": {"file": jcl.name, "sha256": hashlib.sha256(jcl.read_bytes()).hexdigest(), "bytes": jcl.stat().st_size},
        "notice": "PeaCOBOL generated a validated plan only; no network request or job submission was performed.",
    }
    payload["plan_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    return payload
