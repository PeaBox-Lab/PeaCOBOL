from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .audit import append_event, verify_log
from .copybook import parse_copybook, record_length
from .core import build, create_project, doctor, evidence, scan_project
from .records import convert_records, decode_record, hex_view


def _atomic_write(path: Path, data: str) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(data, encoding="utf-8", newline="\n")
    temp.replace(path)


def emit(value: Any, output: str | None = None) -> None:
    data = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if output:
        _atomic_write(Path(output), data)
        print(output)
    else:
        print(data, end="")


def _subject(args: argparse.Namespace) -> Path:
    raw = getattr(args, "path", None) or getattr(args, "file", None) or getattr(args, "copybook", None) or "."
    value = Path(raw).resolve()
    return value if value.is_dir() else value.parent


def _audit_path(args: argparse.Namespace) -> Path:
    if args.audit_log:
        return Path(args.audit_log)
    env = os.environ.get("PEACOBOL_AUDIT_LOG")
    if env:
        return Path(env)
    return _subject(args) / ".peacobol" / "audit.jsonl"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="peacobol", description="Local-first COBOL data, development and assurance toolkit")
    p.add_argument("--audit-log", help="Override the hash-chained local audit log path")
    p.add_argument("--no-audit", action="store_true", help="Disable action audit logging for this invocation")
    sub = p.add_subparsers(dest="cmd", required=True)
    x = sub.add_parser("init", help="Create a project workspace"); x.add_argument("path"); x.add_argument("--name")
    sub.add_parser("doctor", help="Check local tool readiness")
    x = sub.add_parser("scan", help="Analyze COBOL source"); x.add_argument("path", nargs="?", default="."); x.add_argument("-o", "--output")
    x = sub.add_parser("copybook", help="Inspect copybook layout"); x.add_argument("file"); x.add_argument("-o", "--output")
    x = sub.add_parser("decode", help="Decode one fixed-length record"); x.add_argument("copybook"); x.add_argument("file"); x.add_argument("--encoding", default="ascii"); x.add_argument("-o", "--output")
    x = sub.add_parser("convert", help="Convert fixed records to JSONL or CSV"); x.add_argument("copybook"); x.add_argument("file"); x.add_argument("--encoding", default="ascii"); x.add_argument("--format", choices=("jsonl", "csv"), default="jsonl"); x.add_argument("-o", "--output", required=True)
    x = sub.add_parser("hex", help="Create a bounded hex view"); x.add_argument("file"); x.add_argument("--width", type=int, default=16); x.add_argument("--limit", type=int, default=4096); x.add_argument("-o", "--output")
    x = sub.add_parser("build", help="Compile with GnuCOBOL without shell execution"); x.add_argument("path", nargs="?", default="."); x.add_argument("--timeout", type=int, default=60); x.add_argument("-o", "--output")
    x = sub.add_parser("evidence", help="Create a reproducible evidence manifest"); x.add_argument("path", nargs="?", default="."); x.add_argument("-o", "--output")
    x = sub.add_parser("audit-verify", help="Verify a hash-chained audit log"); x.add_argument("file"); x.add_argument("-o", "--output")
    return p


def dispatch(args: argparse.Namespace) -> Any:
    if args.cmd == "init":
        return create_project(Path(args.path), args.name or Path(args.path).name)
    if args.cmd == "doctor":
        return doctor()
    if args.cmd == "scan":
        return scan_project(Path(args.path))
    if args.cmd == "copybook":
        fields = parse_copybook(Path(args.file))
        return {"schema": "peacobol-copybook-2", "record_length": record_length(fields), "fields": [f.to_dict() for f in fields]}
    if args.cmd == "decode":
        fields = parse_copybook(Path(args.copybook))
        return {"schema": "peacobol-record-2", "record": decode_record(fields, Path(args.file).read_bytes(), args.encoding)}
    if args.cmd == "convert":
        fields = parse_copybook(Path(args.copybook))
        data = convert_records(fields, Path(args.file), args.encoding, args.format)
        _atomic_write(Path(args.output), data)
        return {"ok": True, "output": args.output, "format": args.format}
    if args.cmd == "hex":
        if args.limit < 1 or args.limit > 1024 * 1024:
            raise ValueError("Hex limit must be between 1 and 1048576 bytes")
        return {"schema": "peacobol-hex-1", "file": Path(args.file).name, "truncated": Path(args.file).stat().st_size > args.limit, "rows": hex_view(Path(args.file).read_bytes()[:args.limit], args.width)}
    if args.cmd == "build":
        if args.timeout < 1 or args.timeout > 3600:
            raise ValueError("Build timeout must be between 1 and 3600 seconds")
        return build(Path(args.path), args.timeout)
    if args.cmd == "evidence":
        excluded = [Path(args.output)] if args.output else []
        return evidence(Path(args.path), exclude=excluded)
    if args.cmd == "audit-verify":
        return verify_log(Path(args.file))
    raise ValueError(f"Unknown command: {args.cmd}")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    output = getattr(args, "output", None)
    try:
        result = dispatch(args)
        if args.cmd != "convert":
            emit(result, output)
        if not args.no_audit:
            append_event(_audit_path(args), args.cmd, str(_subject(args)), "success", {"output": output, "ok": result.get("ok") if isinstance(result, dict) else None})
        return 0
    except Exception as exc:
        if not args.no_audit:
            try:
                append_event(_audit_path(args), args.cmd, str(_subject(args)), "failure", {"error_type": type(exc).__name__, "message": str(exc)[:500]})
            except Exception:
                pass
        print(json.dumps({"ok": False, "error": str(exc), "error_type": type(exc).__name__}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
