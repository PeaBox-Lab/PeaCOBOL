from __future__ import annotations
import hashlib, json, re, shutil, subprocess
from dataclasses import dataclass, asdict
from pathlib import Path

PIC_RE = re.compile(r"^\s*(\d{2}|77)\s+([A-Z0-9-]+)(?:\s+REDEFINES\s+([A-Z0-9-]+))?.*?\bPIC\s+([SX9V()0-9+\-.,Z*]+)(?:\s+(COMP(?:-[1-5])?|BINARY|PACKED-DECIMAL))?", re.I)
CALL_RE = re.compile(r"\bCALL\s+['\"]([^'\"]+)['\"]", re.I)
COPY_RE = re.compile(r"\bCOPY\s+([A-Z0-9_-]+)", re.I)
PARA_RE = re.compile(r"^\s*([A-Z0-9-]+)\.\s*$", re.I)

@dataclass
class Finding:
    rule: str; severity: str; file: str; line: int; message: str; remediation: str

@dataclass
class Field:
    level: int; name: str; picture: str; usage: str; offset: int; length: int; redefines: str | None = None

def picture_digits(pic: str) -> int:
    total = 0
    for token, n in re.findall(r"([X9AZ*])(?:\((\d+)\))?", pic.upper()):
        total += int(n or 1)
    return total

def storage_length(pic: str, usage: str) -> int:
    digits = picture_digits(pic)
    u = (usage or "DISPLAY").upper()
    if u in ("COMP-3", "PACKED-DECIMAL"):
        return (digits + 2) // 2
    if u in ("COMP", "COMP-4", "BINARY", "COMP-5"):
        return 2 if digits <= 4 else 4 if digits <= 9 else 8
    if u == "COMP-1": return 4
    if u == "COMP-2": return 8
    return digits

def parse_copybook(path: Path) -> list[Field]:
    fields, offset = [], 0
    for line in path.read_text(errors="replace").splitlines():
        m = PIC_RE.search(line)
        if not m: continue
        level, name, redef, pic, usage = m.groups()
        length = storage_length(pic, usage or "DISPLAY")
        fields.append(Field(int(level), name.upper(), pic.upper(), (usage or "DISPLAY").upper(), offset, length, redef.upper() if redef else None))
        if not redef: offset += length
    return fields

def scan_project(root: Path) -> dict:
    files = list(root.rglob("*.cbl")) + list(root.rglob("*.cob")) + list(root.rglob("*.cpy"))
    programs, copybooks, calls, copies, paragraphs, findings = [], [], [], [], [], []
    for p in files:
        rel = str(p.relative_to(root)); text = p.read_text(errors="replace"); lines = text.splitlines()
        if p.suffix.lower() == ".cpy": copybooks.append(rel)
        else: programs.append(rel)
        for i, line in enumerate(lines, 1):
            for x in CALL_RE.findall(line): calls.append({"from": rel, "to": x.upper(), "line": i})
            for x in COPY_RE.findall(line): copies.append({"from": rel, "copybook": x.upper(), "line": i})
            m = PARA_RE.match(line)
            if m: paragraphs.append({"file": rel, "name": m.group(1).upper(), "line": i})
            upper = line.upper()
            if re.search(r"\bGO\s+TO\b", upper): findings.append(Finding("PC001", "high", rel, i, "GO TO reduces control-flow assurance.", "Use scoped PERFORM and explicit terminators."))
            if "STOP RUN" in upper: findings.append(Finding("PC002", "medium", rel, i, "STOP RUN can terminate a calling runtime.", "Prefer GOBACK for reusable programs."))
            if re.search(r"\b(READ|WRITE|REWRITE|DELETE|OPEN|CLOSE)\b", upper) and "FILE STATUS" not in upper and "INVALID KEY" not in upper and "AT END" not in upper:
                findings.append(Finding("PC101", "medium", rel, i, "I/O statement may lack local status handling.", "Define FILE STATUS and verify it after the operation."))
            if "DIVIDE" in upper and "ON SIZE ERROR" not in upper:
                findings.append(Finding("PC201", "high", rel, i, "DIVIDE lacks ON SIZE ERROR handling.", "Add ON SIZE ERROR and validate a non-zero divisor."))
            if re.search(r"\bACCEPT\b", upper): findings.append(Finding("PC301", "low", rel, i, "External input accepted.", "Validate type, range, length and encoding before use."))
    return {"programs": programs, "copybooks": copybooks, "calls": calls, "copy_references": copies, "paragraphs": paragraphs, "findings": [asdict(x) for x in findings]}

def create_project(path: Path, name: str):
    path.mkdir(parents=True, exist_ok=True)
    for d in ("src", "copybooks", "tests", "jcl", "config", "reports"): (path/d).mkdir(exist_ok=True)
    (path/"peacobol.json").write_text(json.dumps({"name": name, "version": "0.1.0", "source": ["src"], "copybooks": ["copybooks"], "profiles": {"banking": {"strict_decimal": True, "audit": True}, "aerospace": {"goto": "error", "reproducible": True}}}, indent=2))
    (path/"src"/"HELLO.cbl").write_text("       IDENTIFICATION DIVISION.\n       PROGRAM-ID. HELLO.\n       PROCEDURE DIVISION.\n           DISPLAY 'HELLO FROM PEACOBOL'.\n           GOBACK.\n")

def doctor() -> dict:
    tools = {x: shutil.which(x) for x in ("cobc", "git", "python")}
    return {"tools": tools, "ready_for_gnucobol": bool(tools["cobc"]), "python_runtime": bool(tools["python"])}

def build(root: Path) -> dict:
    cobc = shutil.which("cobc")
    sources = list(root.rglob("*.cbl")) + list(root.rglob("*.cob"))
    if not cobc: return {"ok": False, "message": "GnuCOBOL cobc was not found. Analysis remains available."}
    out = root/"build"; out.mkdir(exist_ok=True)
    results=[]
    for src in sources:
        target=out/src.stem
        cp=subprocess.run([cobc,"-x","-Wall","-o",str(target),str(src)],capture_output=True,text=True)
        results.append({"source":str(src),"ok":cp.returncode==0,"stdout":cp.stdout,"stderr":cp.stderr})
    return {"ok": all(x["ok"] for x in results), "results": results}

def evidence(root: Path, report: dict) -> dict:
    hashes={}
    for p in sorted(root.rglob("*")):
        if p.is_file() and ".git" not in p.parts and "reports" not in p.parts:
            hashes[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
    return {"schema":"peacobol-evidence-1", "project":str(root), "source_hashes":hashes, "analysis":report, "doctor":doctor()}
