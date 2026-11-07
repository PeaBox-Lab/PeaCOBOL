from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
GENESIS = "0" * 64
def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
def _last_hash(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return GENESIS
    last = ""
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                last = line
    if not last:
        return GENESIS
    return json.loads(last)["event_hash"]
def append_event(path: Path, action: str, subject: str, outcome: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "schema": "peacobol-audit-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": os.environ.get("USER") or os.environ.get("USERNAME") or "local-user",
        "action": action,
        "subject": subject,
        "outcome": outcome,
        "details": details or {},
        "previous_hash": _last_hash(path),
    }
    event["event_hash"] = hashlib.sha256(_canonical(event)).hexdigest()
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return event
def verify_log(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.exists():
        return {"ok": False, "events": 0, "error": "Audit log does not exist"}
    previous = GENESIS
    count = 0
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                return {"ok": False, "events": count, "line": line_number, "error": "Invalid JSON"}
            supplied = event.pop("event_hash", None)
            calculated = hashlib.sha256(_canonical(event)).hexdigest()
            if event.get("previous_hash") != previous:
                return {"ok": False, "events": count, "line": line_number, "error": "Broken previous-hash link"}
            if supplied != calculated:
                return {"ok": False, "events": count, "line": line_number, "error": "Event hash mismatch"}
            previous = supplied
            count += 1
    return {"ok": True, "events": count, "head_hash": previous}
