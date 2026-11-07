from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .diagnostics import normalize_diagnostics

MAX_SPOOL_BYTES = 10 * 1024 * 1024
STEP_RE = re.compile(r"(?:IEF142I\s+\S+\s+|STEP[=\s:]+)(?P<step>[A-Z0-9#$@-]{1,16}).*?(?:RC|CC|RETURN\s+CODE|COND(?:ITION)?\s+CODE)[=\s:]+(?P<rc>\d{1,4})", re.I)
COND_RE = re.compile(r"(?:MAXCC|RETURN\s+CODE|CONDITION\s+CODE|RC)[=\s:]+(?P<rc>\d{1,4})", re.I)
ABEND_RE = re.compile(r"\b(?:ABEND(?:ED)?(?:\s+CODE)?[=\s:]+|SYSTEM\s+COMPLETION\s+CODE[=\s:]+)(?P<code>[A-Z0-9-]{2,16})\b", re.I)
FILE_STATUS_RE = re.compile(r"\b(?:FILE[- ]?STATUS|FS)[=\s:]+(?P<code>[A-Z0-9]{2})\b", re.I)
SOURCE_RE = re.compile(r"\b(?P<file>[A-Za-z0-9_./\\-]+\.(?:cbl|cob|cpy))(?::|\s+LINE[=\s:]+)(?P<line>\d+)\b", re.I)


def read_spool(path: Path) -> tuple[bytes, str]:
    if path.is_symlink():
        raise FileNotFoundError(f"Spool file not found: {path}")
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Spool file not found: {path}")
    if path.stat().st_size > MAX_SPOOL_BYTES:
        raise ValueError(f"Spool input exceeds {MAX_SPOOL_BYTES} bytes")
    data = path.read_bytes()
    return data, data.decode("utf-8", errors="replace")


def parse_spool(text: str) -> dict[str, Any]:
    encoded = text.encode("utf-8")
    if len(encoded) > MAX_SPOOL_BYTES:
        raise ValueError(f"Spool input exceeds {MAX_SPOOL_BYTES} bytes")
    steps: list[dict[str, Any]] = []
    abends: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    source_refs: list[dict[str, Any]] = []
    max_return_code: int | None = None
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        step = STEP_RE.search(line)
        if step:
            rc = int(step.group("rc"))
            steps.append({"step": step.group("step").upper(), "return_code": rc, "spool_line": number})
            max_return_code = rc if max_return_code is None else max(max_return_code, rc)
        else:
            cond = COND_RE.search(line)
            if cond:
                rc = int(cond.group("rc"))
                max_return_code = rc if max_return_code is None else max(max_return_code, rc)
        for match in ABEND_RE.finditer(line):
            abends.append({"code": match.group("code").upper(), "spool_line": number})
        for match in FILE_STATUS_RE.finditer(line):
            statuses.append({"code": match.group("code").upper(), "spool_line": number})
        for match in SOURCE_RE.finditer(line):
            source_refs.append({"file": match.group("file").replace("\\", "/"), "line": int(match.group("line")), "spool_line": number})
    diagnostics = normalize_diagnostics(text)
    failed_steps = [item for item in steps if item["return_code"] != 0]
    return {
        "schema": "peacobol-spool-1",
        "line_count": len(text.splitlines()),
        "max_return_code": max_return_code,
        "steps": steps,
        "failed_steps": failed_steps,
        "abends": abends,
        "file_statuses": statuses,
        "source_references": source_refs,
        "compiler_diagnostics": diagnostics,
        "ok": not abends and not statuses and not failed_steps and not any(item.get("severity") == "error" for item in diagnostics),
    }
