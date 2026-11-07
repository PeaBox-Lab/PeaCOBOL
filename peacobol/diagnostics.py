from __future__ import annotations

import re
from typing import Any

GNU_RE = re.compile(r"^(?P<file>.*?):(?P<line>\d+)(?::(?P<column>\d+))?:\s*(?P<severity>warning|error|note):\s*(?P<message>.*)$", re.I)
GNU_DRIVER_RE = re.compile(r"^(?P<tool>cobc|cobcrun):\s*(?P<severity>warning|error|note|fatal error):\s*(?P<message>.*)$", re.I)
IBM_RE = re.compile(r"^(?P<code>IGY[A-Z0-9]+-[A-Z])\s+(?P<message>.*?)(?:\s+Line:\s*(?P<line>\d+))?$", re.I)


def _ibm_severity(code: str) -> str:
    marker = code.rsplit("-", 1)[-1].upper()
    return {"I": "note", "W": "warning", "E": "error", "S": "error", "U": "error"}.get(marker, "note")


def normalize_diagnostics(text: str, source: str | None = None) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = GNU_RE.match(line)
        if match:
            item: dict[str, Any] = {
                "tool": "gnucobol",
                "severity": match.group("severity").lower(),
                "message": match.group("message").strip(),
                "file": match.group("file") or source,
                "line": int(match.group("line")),
            }
            if match.group("column"):
                item["column"] = int(match.group("column"))
            diagnostics.append(item)
            continue
        match = GNU_DRIVER_RE.match(line)
        if match:
            severity = match.group("severity").lower()
            diagnostics.append({"tool": match.group("tool").lower(), "severity": "error" if severity == "fatal error" else severity, "message": match.group("message").strip(), "file": source})
            continue
        match = IBM_RE.match(line)
        if match:
            item = {
                "tool": "ibm-enterprise-cobol",
                "severity": _ibm_severity(match.group("code")),
                "code": match.group("code").upper(),
                "message": match.group("message").strip(),
                "file": source,
            }
            if match.group("line"):
                item["line"] = int(match.group("line"))
            diagnostics.append(item)
    return diagnostics


def diagnostic_summary(diagnostics: list[dict[str, Any]]) -> dict[str, int]:
    return {severity: sum(item.get("severity") == severity for item in diagnostics) for severity in ("error", "warning", "note")}
