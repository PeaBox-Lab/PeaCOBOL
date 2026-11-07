from __future__ import annotations
import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
from .copybook import Field, parse_copybook, picture_digits, storage_length, record_length
from .diagnostics import diagnostic_summary, normalize_diagnostics
from .profiles import BUILTIN_PROFILES, load_profile, resolve_profile_name
CALL_RE = re.compile(r"\bCALL\s+['\"]([^'\"]+)['\"]", re.I)
COPY_RE = re.compile(r"\bCOPY\s+([A-Z0-9_-]+)", re.I)
PARA_RE = re.compile(r"^\s*([A-Z0-9-]+)\.\s*$", re.I)
EXCLUDED_DIRS = {".git", ".peacobol", "build", "reports", "__pycache__", ".pytest_cache"}
SOURCE_SUFFIXES = {".cbl", ".cob", ".cpy"}
MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_PROJECT_FILES = 10000
@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    file: str
    line: int
    message: str
    remediation: str
def _safe_files(root: Path, suffixes: set[str] | None = None) -> list[Path]:
    root = root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Project directory not found: {root}")
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        if suffixes and path.suffix.lower() not in suffixes:
            continue
        if path.stat().st_size > MAX_SOURCE_BYTES:
            raise ValueError(f"Source file exceeds {MAX_SOURCE_BYTES} bytes: {path.relative_to(root)}")
        files.append(path)
        if len(files) > MAX_PROJECT_FILES:
            raise ValueError(f"Project exceeds {MAX_PROJECT_FILES} files")
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())
def scan_project(root: Path) -> dict:
    root = root.resolve()
    files = _safe_files(root, SOURCE_SUFFIXES)
    programs: list[str] = []
    copybooks: list[str] = []
    calls: list[dict] = []
    copies: list[dict] = []
    paragraphs: list[dict] = []
    findings: list[Finding] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        (copybooks if path.suffix.lower() == ".cpy" else programs).append(rel)
        for number, line in enumerate(lines, 1):
            code = line[6:] if len(line) >= 7 and line[:6].strip().isdigit() else line
            if len(line) >= 7 and line[6] in ("*", "/"):
                continue
            upper = code.upper()
            calls.extend({"from": rel, "to": value.upper(), "line": number} for value in CALL_RE.findall(code))
            copies.extend({"from": rel, "copybook": value.upper(), "line": number} for value in COPY_RE.findall(code))
            paragraph = PARA_RE.match(code)
            if paragraph:
                paragraphs.append({"file": rel, "name": paragraph.group(1).upper(), "line": number})
            if re.search(r"\bGO\s+TO\b", upper):
                findings.append(Finding("PC001", "high", rel, number, "GO TO reduces control-flow assurance.", "Use scoped PERFORM and explicit terminators."))
            if "STOP RUN" in upper:
                findings.append(Finding("PC002", "medium", rel, number, "STOP RUN can terminate a calling runtime.", "Prefer GOBACK for reusable programs."))
            if re.search(r"\b(READ|WRITE|REWRITE|DELETE|OPEN|CLOSE)\b", upper) and not any(x in upper for x in ("FILE STATUS", "INVALID KEY", "AT END")):
                findings.append(Finding("PC101", "medium", rel, number, "I/O statement may lack local status handling.", "Define FILE STATUS and verify it after the operation."))
            if "DIVIDE" in upper and "ON SIZE ERROR" not in upper:
                findings.append(Finding("PC201", "high", rel, number, "DIVIDE lacks ON SIZE ERROR handling.", "Add ON SIZE ERROR and validate a non-zero divisor."))
            if re.search(r"\bACCEPT\b", upper):
                findings.append(Finding("PC301", "low", rel, number, "External input is accepted.", "Validate type, range, length and encoding before use."))
            if re.search(r"\bCALL\s+[A-Z0-9-]+\b", upper) and not CALL_RE.search(code):
                findings.append(Finding("PC401", "medium", rel, number, "Dynamic CALL target requires runtime control.", "Allow-list dynamic targets and record the resolved module."))
    return {
        "schema": "peacobol-scan-3",
        "project": root.name,
        "programs": programs,
        "copybooks": copybooks,
        "calls": calls,
        "copy_references": copies,
        "paragraphs": paragraphs,
        "findings": [asdict(item) for item in findings],
        "summary": {
            "programs": len(programs),
            "copybooks": len(copybooks),
            "calls": len(calls),
            "findings": {severity: sum(x.severity == severity for x in findings) for severity in ("critical", "high", "medium", "low")},
        },
    }
def create_project(path: Path, name: str) -> dict:
    path = path.resolve()
    path.mkdir(parents=True, exist_ok=True)
    for directory in ("src", "copybooks", "tests", "jcl", "config", "reports", ".peacobol"):
        (path / directory).mkdir(exist_ok=True)
    config = {
        "name": name,
        "version": "0.3.0",
        "source": ["src"],
        "copybooks": ["copybooks"],
        "default_profile": "development",
        "profiles": {name: {} for name in BUILTIN_PROFILES},
    }
    (path / "peacobol.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    hello = path / "src" / "HELLO.cbl"
    if not hello.exists():
        hello.write_text("       IDENTIFICATION DIVISION.\n       PROGRAM-ID. HELLO.\n       PROCEDURE DIVISION.\n           DISPLAY 'HELLO FROM PEACOBOL'.\n           GOBACK.\n", encoding="utf-8")
    return {"ok": True, "project": name, "path": str(path)}
def doctor() -> dict:
    tools = {name: shutil.which(name) for name in ("cobc", "git", "python")}
    return {
        "schema": "peacobol-doctor-3",
        "tools": tools,
        "ready_for_analysis": True,
        "ready_for_gnucobol": bool(tools["cobc"]),
        "recommendations": [] if tools["cobc"] else ["Install GnuCOBOL to enable compilation; analysis and data tools remain available."],
    }
def build(root: Path, timeout: int = 60, profile_name: str | None = None) -> dict:
    root = root.resolve()
    profile_name = resolve_profile_name(root, profile_name, "development")
    profile = load_profile(root, profile_name)
    sources = [p for p in _safe_files(root, {".cbl", ".cob"})]
    cobc = shutil.which("cobc")
    if not cobc:
        return {"schema": "peacobol-build-3", "ok": False, "profile": profile_name, "message": "GnuCOBOL cobc was not found. Analysis remains available.", "diagnostics": [], "diagnostic_summary": diagnostic_summary([]), "results": [], "manifest": None}
    output_root = root / "build"
    results: list[dict] = []
    all_diagnostics: list[dict] = []
    copy_dirs = sorted({str(p.parent) for p in _safe_files(root, {".cpy"})})
    base_targets: dict[Path, list[Path]] = {}
    for source in sources:
        relative = source.relative_to(root)
        base_targets.setdefault(relative.with_suffix(""), []).append(source)
    target_names: dict[Path, Path] = {}
    for base, members in base_targets.items():
        for source in members:
            target_names[source] = base if len(members) == 1 else base.with_name(f"{base.name}-{source.suffix.lower().lstrip('.')}")
    compiler = profile["compiler"]
    flags = list(compiler.get("flags", []))
    if compiler.get("optimize") and "-O2" not in flags:
        flags.append("-O2")
    if compiler.get("dialect") == "ibm":
        flags.append("-std=ibm")
    for source in sources:
        relative = source.relative_to(root)
        target = output_root / target_names[source]
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            if not target.is_file() and not target.is_symlink():
                raise ValueError(f"Build target is not a file: {target.relative_to(root)}")
            target.unlink()
        args = [cobc, "-x", *flags]
        for copy_dir in copy_dirs:
            args.extend(["-I", copy_dir])
        args.extend(["-o", str(target), str(source)])
        try:
            completed = subprocess.run(args, capture_output=True, text=True, timeout=timeout, shell=False, check=False)
            stdout = completed.stdout[-100000:]
            stderr = completed.stderr[-100000:]
            diagnostics = normalize_diagnostics(stderr + "\n" + stdout, relative.as_posix())
            artifact_exists = target.is_file()
            if completed.returncode == 0 and not artifact_exists:
                diagnostics.append({"tool": "peacobol", "severity": "error", "message": "Compiler returned success but did not create the expected artifact.", "file": relative.as_posix()})
            all_diagnostics.extend(diagnostics)
            result = {
                "source": relative.as_posix(),
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "target": target.relative_to(root).as_posix(),
                "ok": completed.returncode == 0 and artifact_exists,
                "return_code": completed.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "diagnostics": diagnostics,
                "diagnostic_summary": diagnostic_summary(diagnostics),
            }
            if result["ok"]:
                result["artifact_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            results.append(result)
        except subprocess.TimeoutExpired as exc:
            results.append({"source": relative.as_posix(), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "target": target.relative_to(root).as_posix(), "ok": False, "timed_out": True, "timeout_seconds": timeout, "stdout": (exc.stdout or "")[-100000:], "stderr": (exc.stderr or "")[-100000:], "diagnostics": [], "diagnostic_summary": diagnostic_summary([])})
    manifest = {
        "schema": "peacobol-build-manifest-1",
        "profile": profile_name,
        "compiler": "cobc",
        "flags": flags,
        "sources": [{key: result[key] for key in ("source", "source_sha256", "target", "artifact_sha256") if key in result} for result in results],
    }
    manifest["manifest_hash"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"schema": "peacobol-build-3", "ok": bool(results) and all(x["ok"] for x in results), "profile": profile_name, "compiler": "cobc", "timeout_seconds": timeout, "diagnostics": all_diagnostics, "diagnostic_summary": diagnostic_summary(all_diagnostics), "results": results, "manifest": manifest}
def evidence(root: Path, report: dict | None = None, exclude: Iterable[Path] = ()) -> dict:
    root = root.resolve()
    excluded = {path.resolve() for path in exclude}
    hashes: dict[str, str] = {}
    for path in _safe_files(root):
        if path.resolve() in excluded:
            continue
        rel = path.relative_to(root).as_posix()
        hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    analysis = report if report is not None else scan_project(root)
    payload = {
        "schema": "peacobol-evidence-3",
        "project": root.name,
        "source_hashes": hashes,
        "analysis": analysis,
    }
    payload["manifest_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return payload
__all__ = ["Field", "parse_copybook", "picture_digits", "storage_length", "record_length", "scan_project", "create_project", "doctor", "build", "evidence"]
