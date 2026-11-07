from __future__ import annotations
import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
GENESIS = "0" * 64
def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))
def _reject_symlink_components(path: Path) -> None:
    path = _absolute(path)
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Audit path may not contain symlinks: {path}")
def _open_text(path: Path, flags: int):
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags | nofollow, 0o600)
    mode = "a" if flags & os.O_APPEND else "r"
    return os.fdopen(descriptor, mode, encoding="utf-8", newline="\n")
@contextmanager
def _exclusive_lock(path: Path):
    lock_path = path.with_name(path.name + ".lock")
    _reject_symlink_components(lock_path)
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        if os.name == "nt":
            import msvcrt
            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"0")
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
def _last_hash(path: Path) -> str:
    _reject_symlink_components(path)
    if not path.exists() or path.stat().st_size == 0:
        return GENESIS
    last = ""
    with _open_text(path, os.O_RDONLY) as handle:
        for line in handle:
            if line.strip():
                last = line
    if not last:
        return GENESIS
    return json.loads(last)["event_hash"]
def append_event(path: Path, action: str, subject: str, outcome: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    path = _absolute(path)
    _reject_symlink_components(path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(path)
    with _exclusive_lock(path):
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
        with _open_text(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND) as handle:
            handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return event
def verify_log(path: Path) -> dict[str, Any]:
    path = _absolute(path)
    try:
        _reject_symlink_components(path)
    except ValueError as exc:
        return {"ok": False, "events": 0, "error": str(exc)}
    with _exclusive_lock(path):
        if not path.exists():
            return {"ok": False, "events": 0, "error": "Audit log does not exist"}
        previous = GENESIS
        count = 0
        with _open_text(path, os.O_RDONLY) as handle:
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
