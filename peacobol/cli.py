from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from .assurance import analyze_assurance
from .audit import append_event, verify_log
from .copybook import parse_copybook, record_length
from .coverage import import_coverage
from .enterprise import db2_compatibility, resource_inventory, submission_plan
from .impact import compare_copybooks
from .core import build, create_project, doctor, evidence, scan_project
from .investigation import diagnose, failure_bundle
from .jcl import generate_jcl
from .knowledge import list_knowledge, load_catalog, lookup
from .policy import evaluate_policy
from .profiles import list_profiles, load_profile, resolve_profile_name
from .records import convert_records, decode_record, hex_view
from .rulesintegrity import rules_manifest, verify_rules_manifest
from .sarif import to_sarif
from .spool import read_spool
from .supplychain import attest, immutable_export, retention_plan, sbom, sign_release, verify_attestation, verify_release
from .testworkbench import cobol_check_stub, compare_golden, generate_cases
from .gui import start_gui
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
    raw = getattr(args, "path", None) or getattr(args, "project", None) or getattr(args, "file", None) or getattr(args, "copybook", None) or "."
    value = Path(raw).resolve()
    return value if value.is_dir() else value.parent
def _audit_path(args: argparse.Namespace) -> Path:
    if args.audit_log:
        return Path(args.audit_log)
    env = os.environ.get("PEACOBOL_AUDIT_LOG")
    if env:
        return Path(env)
    return _subject(args) / ".peacobol" / "audit.jsonl"
def _add_profile(parser: argparse.ArgumentParser, default: str | None = None) -> None:
    parser.add_argument("--profile", default=None, choices=("development", "release", "banking", "aerospace"))
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="peacobol", description="Local-first COBOL data, development and assurance toolkit")
    p.add_argument("--audit-log", help="Override the hash-chained local audit log path")
    p.add_argument("--no-audit", action="store_true", help="Disable action audit logging for this invocation")
    sub = p.add_subparsers(dest="cmd", required=True)
    x = sub.add_parser("init", help="Create a project workspace"); x.add_argument("path"); x.add_argument("--name")
    sub.add_parser("doctor", help="Check local tool readiness")
    x = sub.add_parser("scan", help="Analyze COBOL source"); x.add_argument("path", nargs="?", default="."); x.add_argument("-o", "--output")
    x = sub.add_parser("copybook", help="Inspect copybook layout"); x.add_argument("file"); x.add_argument("-o", "--output")
    x = sub.add_parser("decode", help="Decode one fixed-length record"); x.add_argument("copybook"); x.add_argument("file"); x.add_argument("--project", default="."); x.add_argument("--encoding"); _add_profile(x); x.add_argument("-o", "--output")
    x = sub.add_parser("convert", help="Convert fixed records to JSONL or CSV"); x.add_argument("copybook"); x.add_argument("file"); x.add_argument("--project", default="."); x.add_argument("--encoding"); _add_profile(x); x.add_argument("--format", choices=("jsonl", "csv"), default="jsonl"); x.add_argument("-o", "--output", required=True)
    x = sub.add_parser("hex", help="Create a bounded hex view"); x.add_argument("file"); x.add_argument("--width", type=int, default=16); x.add_argument("--limit", type=int, default=4096); x.add_argument("-o", "--output")
    x = sub.add_parser("build", help="Compile with a versioned build profile"); x.add_argument("path", nargs="?", default="."); x.add_argument("--timeout", type=int, default=60); _add_profile(x); x.add_argument("-o", "--output")
    x = sub.add_parser("evidence", help="Create a reproducible evidence manifest"); x.add_argument("path", nargs="?", default="."); x.add_argument("-o", "--output")
    x = sub.add_parser("audit-verify", help="Verify a hash-chained audit log"); x.add_argument("file"); x.add_argument("-o", "--output")
    x = sub.add_parser("profiles", help="List or inspect versioned profiles"); x.add_argument("path", nargs="?", default="."); x.add_argument("--name", choices=("development", "release", "banking", "aerospace")); x.add_argument("-o", "--output")
    x = sub.add_parser("jcl", help="Generate IBM Enterprise COBOL compile/link/run JCL"); x.add_argument("path", nargs="?", default="."); x.add_argument("program"); _add_profile(x, "release"); x.add_argument("--source-dataset", default="USER.COBOL.SOURCE"); x.add_argument("--load-dataset", default="USER.COBOL.LOAD"); x.add_argument("--copybook-dataset"); x.add_argument("--no-run", action="store_true"); x.add_argument("-o", "--output", required=True)
    x = sub.add_parser("gate", help="Evaluate profile policy gates"); x.add_argument("path", nargs="?", default="."); _add_profile(x, "release"); x.add_argument("--with-build", action="store_true"); x.add_argument("--with-evidence", action="store_true"); x.add_argument("--timeout", type=int, default=60); x.add_argument("-o", "--output")
    x = sub.add_parser("knowledge", help="List or inspect diagnostic knowledge catalogs"); x.add_argument("path", nargs="?", default="."); x.add_argument("--kind", choices=("abend", "file-status")); x.add_argument("--code"); x.add_argument("-o", "--output")
    x = sub.add_parser("diagnose", help="Analyze spool output and correlate source context"); x.add_argument("path", nargs="?", default="."); x.add_argument("spool"); x.add_argument("--context-lines", type=int, default=3); x.add_argument("-o", "--output")
    x = sub.add_parser("failure-bundle", help="Create a deterministic hashed failure bundle"); x.add_argument("path", nargs="?", default="."); x.add_argument("spool"); x.add_argument("--context-lines", type=int, default=3); x.add_argument("-o", "--output", required=True)
    x = sub.add_parser("assure", help="Build assurance graphs, inventories and findings"); x.add_argument("path", nargs="?", default="."); x.add_argument("--fail-on", choices=("none", "critical", "high", "medium", "low"), default="none"); x.add_argument("--format", choices=("json", "sarif"), default="json"); x.add_argument("-o", "--output")
    x = sub.add_parser("impact", help="Compare two copybook versions field by field"); x.add_argument("before"); x.add_argument("after"); x.add_argument("--fail-on-breaking", action="store_true"); x.add_argument("-o", "--output")
    x = sub.add_parser("test-cases", help="Generate boundary and invalid records from a copybook"); x.add_argument("copybook"); x.add_argument("--encoding", choices=("ascii", "utf-8", "cp037", "cp500"), default="ascii"); x.add_argument("--byteorder", choices=("big", "little"), default="big"); x.add_argument("--unsigned", action="store_true"); x.add_argument("--cobol-check-program"); x.add_argument("-o", "--output")
    x = sub.add_parser("golden", help="Compare actual and expected binary outputs"); x.add_argument("actual"); x.add_argument("expected"); x.add_argument("--fail-on-difference", action="store_true"); x.add_argument("-o", "--output")
    x = sub.add_parser("coverage", help="Import normalized JSON line coverage"); x.add_argument("file"); x.add_argument("--evidence-manifest"); x.add_argument("--project"); x.add_argument("--minimum", type=float); x.add_argument("-o", "--output")
    x = sub.add_parser("db2-check", help="Compare copybook fields with DB2 DDL columns"); x.add_argument("copybook"); x.add_argument("ddl"); x.add_argument("--fail-on-incompatible", action="store_true"); x.add_argument("-o", "--output")
    x = sub.add_parser("resources", help="Inventory DB2, CICS and MQ references"); x.add_argument("path", nargs="?", default="."); x.add_argument("-o", "--output")
    x = sub.add_parser("submission-plan", help="Validate an offline Zowe or zOSMF submission plan"); x.add_argument("path", nargs="?", default="."); x.add_argument("jcl"); x.add_argument("--system", required=True); x.add_argument("--allowlist", required=True); x.add_argument("--role", required=True); x.add_argument("--credential-reference", required=True); x.add_argument("-o", "--output")
    x = sub.add_parser("sbom", help="Create an offline CycloneDX-style software inventory"); x.add_argument("path", nargs="?", default="."); x.add_argument("-o", "--output")
    x = sub.add_parser("attest", help="Create a local in-toto-style attestation"); x.add_argument("file"); x.add_argument("--verify", action="store_true"); x.add_argument("-o", "--output")
    x = sub.add_parser("immutable-export", help="Create a content-addressed evidence archive"); x.add_argument("files", nargs="+"); x.add_argument("-o", "--output", required=True)
    x = sub.add_parser("retention-plan", help="Create a dry-run retention plan"); x.add_argument("directory"); x.add_argument("--days", type=int, required=True); x.add_argument("-o", "--output")
    x = sub.add_parser("rules-manifest", help="Emit the rule-definition integrity manifest"); x.add_argument("-o", "--output")
    x = sub.add_parser("rules-verify", help="Verify a report's embedded rules manifest"); x.add_argument("report"); x.add_argument("-o", "--output")
    x = sub.add_parser("sign-release", help="Create an HMAC-signed immutable release archive"); x.add_argument("files", nargs="+"); x.add_argument("--release-name", required=True); x.add_argument("-o", "--output", required=True)
    x = sub.add_parser("verify-release", help="Verify a signed release against its archive"); x.add_argument("envelope"); x.add_argument("archive"); x.add_argument("-o", "--output")
    return p
def _select_profile(args: argparse.Namespace, root: Path, fallback: str) -> str:
    selected = resolve_profile_name(root, args.profile, fallback)
    args.profile = selected
    return selected
def _profile_data(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.project)
    return load_profile(root, _select_profile(args, root, "development"))["data"]
def dispatch(args: argparse.Namespace) -> Any:
    if args.cmd == "init":
        return create_project(Path(args.path), args.name or Path(args.path).name)
    if args.cmd == "doctor":
        return doctor()
    if args.cmd == "scan":
        return scan_project(Path(args.path))
    if args.cmd == "copybook":
        fields = parse_copybook(Path(args.file))
        return {"schema": "peacobol-copybook-3", "record_length": record_length(fields), "fields": [f.to_dict() for f in fields]}
    if args.cmd == "decode":
        fields = parse_copybook(Path(args.copybook)); data = _profile_data(args); encoding = args.encoding or data["encoding"]
        return {"schema": "peacobol-record-3", "profile": args.profile, "encoding": encoding, "record": decode_record(fields, Path(args.file).read_bytes(), encoding, data["binary_byteorder"], data["binary_signed"])}
    if args.cmd == "convert":
        fields = parse_copybook(Path(args.copybook)); data = _profile_data(args); encoding = args.encoding or data["encoding"]
        converted = convert_records(fields, Path(args.file), encoding, args.format, data["binary_byteorder"], data["binary_signed"])
        _atomic_write(Path(args.output), converted)
        return {"ok": True, "output": args.output, "format": args.format, "profile": args.profile, "encoding": encoding}
    if args.cmd == "hex":
        if args.limit < 1 or args.limit > 1024 * 1024:
            raise ValueError("Hex limit must be between 1 and 1048576 bytes")
        return {"schema": "peacobol-hex-1", "file": Path(args.file).name, "truncated": Path(args.file).stat().st_size > args.limit, "rows": hex_view(Path(args.file).read_bytes()[:args.limit], args.width)}
    if args.cmd == "build":
        if args.timeout < 1 or args.timeout > 3600:
            raise ValueError("Build timeout must be between 1 and 3600 seconds")
        root = Path(args.path)
        return build(root, args.timeout, _select_profile(args, root, "development"))
    if args.cmd == "evidence":
        excluded = [Path(args.output)] if args.output else []
        return evidence(Path(args.path), exclude=excluded)
    if args.cmd == "audit-verify":
        return verify_log(Path(args.file))
    if args.cmd == "profiles":
        return load_profile(Path(args.path), args.name) if args.name else list_profiles(Path(args.path))
    if args.cmd == "jcl":
        root = Path(args.path)
        selected = _select_profile(args, root, "release")
        result = generate_jcl(root, args.program, selected, args.source_dataset, args.load_dataset, args.copybook_dataset, not args.no_run)
        _atomic_write(Path(args.output), result.pop("jcl"))
        return {"ok": True, "output": args.output, **result}
    if args.cmd == "gate":
        root = Path(args.path); selected = _select_profile(args, root, "release"); profile = load_profile(root, selected); scan = scan_project(root)
        build_report = build(root, args.timeout, selected) if args.with_build else None
        evidence_report = evidence(root, scan) if args.with_evidence else None
        return evaluate_policy(profile, scan, build_report, evidence_report)
    if args.cmd == "knowledge":
        root = Path(args.path)
        if args.code and not args.kind:
            raise ValueError("--code requires --kind")
        if args.code:
            return lookup(root, args.kind, args.code)
        if args.kind:
            return {"schema": "peacobol-knowledge-list-1", "catalogs": {args.kind: load_catalog(root, args.kind)}}
        return list_knowledge(root)
    if args.cmd == "diagnose":
        _, spool_text = read_spool(Path(args.spool))
        return diagnose(Path(args.path), spool_text, args.context_lines)
    if args.cmd == "failure-bundle":
        return failure_bundle(Path(args.path), Path(args.spool), args.output, args.context_lines)
    if args.cmd == "assure":
        report = analyze_assurance(Path(args.path), args.fail_on)
        return to_sarif(report) if args.format == "sarif" else report
    if args.cmd == "impact":
        report = compare_copybooks(Path(args.before), Path(args.after))
        report["ok"] = not (args.fail_on_breaking and not report["compatible"])
        report["gate"] = {"fail_on_breaking": args.fail_on_breaking, "ok": report["ok"]}
        return report
    if args.cmd == "test-cases":
        report = generate_cases(Path(args.copybook), args.encoding, args.byteorder, not args.unsigned)
        if args.cobol_check_program:
            report["cobol_check"] = cobol_check_stub(args.cobol_check_program, report)
        return report
    if args.cmd == "golden":
        report = compare_golden(Path(args.actual), Path(args.expected))
        report["gate"] = {"fail_on_difference": args.fail_on_difference, "ok": report["ok"] or not args.fail_on_difference}
        report["ok"] = report["gate"]["ok"]
        return report
    if args.cmd == "coverage":
        if args.minimum is not None and (args.minimum < 0 or args.minimum > 100):
            raise ValueError("Minimum coverage must be between 0 and 100")
        if args.minimum is not None and (not args.evidence_manifest or not args.project):
            raise ValueError("A minimum coverage gate requires --evidence-manifest and --project")
        report = import_coverage(Path(args.file), Path(args.evidence_manifest) if args.evidence_manifest else None, Path(args.project) if args.project else None)
        passed = args.minimum is None or report["summary"]["percent"] >= args.minimum
        report["gate"] = {"minimum": args.minimum, "ok": passed}
        report["ok"] = passed
        return report
    if args.cmd == "db2-check":
        report = db2_compatibility(Path(args.copybook), Path(args.ddl))
        report["gate"] = {"fail_on_incompatible": args.fail_on_incompatible, "ok": report["ok"] or not args.fail_on_incompatible}
        report["ok"] = report["gate"]["ok"]
        return report
    if args.cmd == "resources":
        return resource_inventory(Path(args.path))
    if args.cmd == "submission-plan":
        return submission_plan(Path(args.path), Path(args.jcl), args.system, Path(args.allowlist), args.role, args.credential_reference)
    if args.cmd == "sbom":
        return sbom(Path(args.path))
    if args.cmd == "attest":
        if args.verify:
            envelope = json.loads(Path(args.file).read_text(encoding="utf-8"))
            return verify_attestation(envelope)
        return attest(Path(args.file))
    if args.cmd == "immutable-export":
        return immutable_export([Path(value) for value in args.files], Path(args.output))
    if args.cmd == "retention-plan":
        return retention_plan(Path(args.directory), args.days)
    if args.cmd == "rules-manifest":
        return rules_manifest()
    if args.cmd == "rules-verify":
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        result = verify_rules_manifest(report.get("rules_manifest", report))
        result["ok"] = result["ok"] and bool(report.get("ok", True))
        return result
    if args.cmd == "sign-release":
        return sign_release([Path(value) for value in args.files], Path(args.output), args.release_name)
    if args.cmd == "verify-release":
        envelope = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
        result = verify_release(envelope, Path(args.archive))
        return result if result["ok"] else (_ for _ in ()).throw(ValueError(result.get("error", "release verification failed")))
    raise ValueError(f"Unknown command: {args.cmd}")
def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    output = getattr(args, "output", None)
    try:
        result = dispatch(args)
        if args.cmd not in ("convert", "jcl", "immutable-export"):
            emit(result, output)
        elif args.cmd == "immutable-export":
            emit(result)
        if not args.no_audit:
            append_event(_audit_path(args), args.cmd, str(_subject(args)), "success", {"output": output, "ok": result.get("ok") if isinstance(result, dict) else None, "profile": getattr(args, "profile", None)})
        gate_ok = result.get("ok", True)
        if args.cmd == "assure" and args.format == "sarif":
            gate_ok = result["runs"][0].get("properties", {}).get("gate", {}).get("ok", True)
        verification_command = args.cmd == "attest" and getattr(args, "verify", False)
        return 3 if (args.cmd in ("gate", "assure", "impact", "golden", "coverage", "db2-check") or verification_command) and not gate_ok else 0
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
