"""Result export for PeaCOBOL GUI workbench runs.

Saves workbench JSON reports beneath the project's reports directory and
records an audit event for every export so local action history stays
consistent with CLI and server behavior.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audit import append_event


MAX_EXPORT_BYTES = 10 * 1024 * 1024  # 10 MiB cap for a single JSON report


def export_report(project_root: Path, view: str, result: Any, output: Path | None = None) -> Path:
    """Write a workbench result as JSON and return the output path.

    The report lands in ``<project>/reports/gui/`` unless an explicit
    path is provided. Directory structure is created on demand and the
    payload never exceeds MAX_EXPORT_BYTES.
    """
    project_root = Path(project_root).resolve()
    if not project_root.is_dir():
        raise NotADirectoryError("Project directory was not found")

    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    encoded = payload.encode("utf-8")
    if len(encoded) > MAX_EXPORT_BYTES:
        raise ValueError("Report exceeds the 10 MiB export limit")

    if output is None:
        output = project_root / "reports" / "gui" / f"{view}.json"
    output = Path(output).resolve()
    output.relative_to(project_root)
    if any(part.is_symlink() for part in output.parents):
        raise ValueError("Symlink paths are not allowed in export targets")

    output.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(output, encoded)

    append_event(
        project_root / ".peacobol" / "audit.jsonl",
        f"gui-export-{view}",
        project_root.name,
        "success",
        {"output": str(output.relative_to(project_root)), "bytes": len(encoded)},
    )
    return output


def write_atomic(path: Path, data: bytes) -> None:
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(data)
    temp.replace(path)


def list_exports(project_root: Path) -> list[dict[str, Any]]:
    """Return metadata for previously exported GUI reports, newest first."""
    reports_dir = Path(project_root).resolve() / "reports" / "gui"
    if not reports_dir.is_dir():
        return []
    exports = []
    for path in sorted(reports_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        exports.append({
            "view": path.stem,
            "path": str(path.relative_to(project_root)),
            "bytes": path.stat().st_size,
            "modified": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        })
    return exports
