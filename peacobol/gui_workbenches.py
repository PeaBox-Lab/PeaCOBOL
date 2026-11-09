"""Additional GUI workbenches: records decode/convert and knowledge lookup.

Extends both the web (server.py) and desktop (gui.py) interfaces with
two workbenches that were previously CLI-only:
  - "Records": decode a fixed-length record with a copybook, show field
    values and a hex view.
  - "Knowledge": look up an ABEND or COBOL file-status code in the
    built-in (or site) knowledge catalog.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def decode_record_view(copybook: Path, data: Path, encoding: str = "ascii") -> dict[str, Any]:
    """Decode one fixed-length record and return a structured report."""
    from .copybook import parse_copybook
    from .records import decode_record, hex_view
    fields = parse_copybook(copybook)
    raw = data.read_bytes()
    record = decode_record(fields, raw, encoding)
    return {
        "schema": "peacobol-gui-records-1",
        "copybook": copybook.name,
        "file": data.name,
        "bytes": len(raw),
        "encoding": encoding,
        "record": record,
        "hex": hex_view(raw[:256], 16),
    }


def knowledge_view(root: Path, kind: str, code: str) -> dict[str, Any]:
    """Look up an ABEND or file-status code in the knowledge catalog."""
    from .knowledge import lookup
    return lookup(root, kind, code)
