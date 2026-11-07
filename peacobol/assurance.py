from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .copybook import parse_copybook
from .core import Finding, SOURCE_SUFFIXES, _safe_files, scan_project

PROGRAM_ID_RE = re.compile(r"\bPROGRAM-ID\.?\s+([A-Z0-9-]+)", re.I)
COPY_RE = re.compile(r"\bCOPY\s+([A-Z0-9_-]+)", re.I)
CALL_RE = re.compile(r"\bCALL\s+['\"]([^'\"]+)['\"]", re.I)
PARAGRAPH_RE = re.compile(r"^\s*([A-Z0-9-]+)\.\s*$", re.I)
PERFORM_RE = re.compile(r"\bPERFORM\s+([A-Z0-9-]+)", re.I)
GOTO_RE = re.compile(r"\bGO\s+TO\b", re.I)
IDENT_RE = re.compile(r"\b[A-Z][A-Z0-9-]{1,}\b", re.I)
SUBSCRIPT_RE = re.compile(r"\b([A-Z][A-Z0-9-]*)\s*\(([^)]+)\)", re.I)
MOVE_RE = re.compile(r"\bMOVE\s+(.+?)\s+TO\s+(.+?)(?:\s+(?:ON\s+SIZE\s+ERROR|NOT\s+ON\s+SIZE\s+ERROR|END-MOVE)\b|$)", re.I)
COMPUTE_RE = re.compile(r"\bCOMPUTE\s+(.+?)\s*=\s*(.+)", re.I)
ACCEPT_RE = re.compile(r"\bACCEPT\s+(.+?)(?:\s+FROM\b|$)", re.I)
WRITE_RE = re.compile(r"\b(?:MOVE\s+.+?\s+TO|COMPUTE|ADD\s+.+?\s+TO|SUBTRACT\s+.+?\s+FROM|MULTIPLY\s+.+?\s+BY|DIVIDE\s+.+?\s+INTO|ACCEPT)\s+([A-Z][A-Z0-9-]*)", re.I)
KEYWORDS = {"MOVE", "TO", "FROM", "BY", "INTO", "GIVING", "COMPUTE", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "CALL", "PERFORM", "GO", "IF", "ELSE", "END-IF", "DISPLAY", "ACCEPT", "READ", "WRITE", "REWRITE", "DELETE", "OPEN", "CLOSE", "STOP", "RUN", "GOBACK", "VALUE", "ZERO", "ZEROS", "SPACE", "SPACES", "OF", "IN", "ROUNDED"}
SEVERITY_RANK = {"none": -1, "critical": 0, "high": 1, "medium": 2, "low": 3}


def _code_lines(path: Path) -> list[tuple[int, str]]:
    result = []
    for number, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if len(raw) >= 7 and raw[6] in ("*", "/"):
            continue
        code = raw[6:] if len(raw) >= 7 and raw[:6].strip().isdigit() else raw
        result.append((number, code))
    return result


def _field_layouts(root: Path) -> dict[str, list[dict[str, int]]]:
    layouts: dict[str, list[dict[str, int]]] = {}
    aliases: dict[str, list[tuple[str, dict[str, int]]]] = {}
    def visit(nodes, ancestors):
        for field in nodes:
            parts = [field.name, *reversed(ancestors)]
            canonical = " OF ".join(parts)
            if field.elementary:
                value = {"length": field.length, "occurs_min": field.occurs_min, "occurs": field.occurs}
                layouts.setdefault(canonical, []).append(value)
                for count in range(1, len(parts)):
                    aliases.setdefault(" OF ".join(parts[:count]), []).append((canonical, value))
            visit(field.children, [*ancestors, field.name])
    for path in _safe_files(root, {".cpy"}):
        visit(parse_copybook(path), [])
    for alias, definitions in aliases.items():
        canonical_names = {name for name, _ in definitions}
        if len(canonical_names) == 1:
            layouts[alias] = [value for _, value in definitions]
    return layouts


def _program_graph(root: Path, programs: list[Path]) -> dict[str, Any]:
    identities: dict[Path, str] = {}
    for path in programs:
        text = path.read_text(encoding="utf-8", errors="replace")
        match = PROGRAM_ID_RE.search(text)
        identities[path] = (match.group(1) if match else path.stem).upper()
    known = set(identities.values())
    edges = []
    for path in programs:
        rel = path.relative_to(root).as_posix()
        for number, code in _code_lines(path):
            for target in CALL_RE.findall(code):
                target = target.upper()
                edges.append({"from": identities[path], "to": target, "file": rel, "line": number, "resolved": target in known})
    return {"nodes": [{"id": identities[path], "file": path.relative_to(root).as_posix()} for path in programs], "edges": edges}


def _copy_graph(root: Path, files: list[Path]) -> dict[str, Any]:
    copybooks = [path for path in files if path.suffix.lower() == ".cpy"]
    by_name = {path.stem.upper(): path.relative_to(root).as_posix() for path in copybooks}
    edges = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        for number, code in _code_lines(path):
            for name in COPY_RE.findall(code):
                key = name.upper()
                edges.append({"from": rel, "copybook": key, "to": by_name.get(key), "line": number, "resolved": key in by_name})
    return {"nodes": sorted(by_name.values()), "edges": edges}


def _data_references(text: str) -> tuple[list[str], list[str]]:
    references: list[str] = []
    indexes: list[str] = []
    tokens = text.replace(",", " ").split()
    position = 0
    while position < len(tokens):
        token = tokens[position].upper().rstrip(".")
        match = re.fullmatch(r"([A-Z][A-Z0-9-]*)(?:\(([^)]+)\))?", token)
        if not match or match.group(1) in KEYWORDS:
            position += 1
            continue
        parts = [match.group(1)]
        if match.group(2):
            indexes.extend(item.upper() for item in IDENT_RE.findall(match.group(2)) if item.upper() not in KEYWORDS)
        position += 1
        while position + 1 < len(tokens) and tokens[position].upper() in {"OF", "IN"}:
            qualifier = tokens[position + 1].upper().rstrip(".")
            if not re.fullmatch(r"[A-Z][A-Z0-9-]*", qualifier) or qualifier in KEYWORDS:
                break
            parts.append(qualifier)
            position += 2
        references.append(" OF ".join(parts))
    return references, indexes


def _goto_targets(code: str) -> tuple[list[str], bool]:
    match = GOTO_RE.search(code)
    if not match:
        return [], False
    tail = code[match.end():].strip().rstrip(".")
    parts = re.split(r"\s+DEPENDING\s+ON\s+", tail, maxsplit=1, flags=re.I)
    targets = [name.upper() for name in IDENT_RE.findall(parts[0]) if name.upper() not in KEYWORDS]
    return targets, len(parts) == 2


def _access_and_flow(root: Path, programs: list[Path], layouts: dict[str, list[dict[str, int]]]) -> tuple[list[dict], list[dict], list[dict], list[Finding]]:
    access: list[dict] = []
    controls: list[dict] = []
    flows: list[dict] = []
    findings: list[Finding] = []
    for path in programs:
        rel = path.relative_to(root).as_posix()
        paragraph = "ENTRY"
        prior_paragraph: str | None = None
        paragraph_terminated = False
        conditional_depth = 0
        tainted: set[str] = set()
        for number, code in _code_lines(path):
            upper = code.upper()
            stripped = upper.strip()
            if re.match(r"^IF\b", stripped):
                conditional_depth += 1
            conditional_assignment = conditional_depth > 0
            para_match = PARAGRAPH_RE.match(code)
            if para_match:
                current = para_match.group(1).upper()
                if prior_paragraph and prior_paragraph != current and not paragraph_terminated:
                    controls.append({"file": rel, "from": prior_paragraph, "to": current, "type": "fallthrough", "line": number})
                prior_paragraph = current
                paragraph = current
                paragraph_terminated = False
                conditional_depth = 0
                continue
            for target in PERFORM_RE.findall(code):
                controls.append({"file": rel, "from": paragraph, "to": target.upper(), "type": "perform", "line": number})
            goto_targets, computed_goto = _goto_targets(code)
            for target in goto_targets:
                controls.append({"file": rel, "from": paragraph, "to": target, "type": "computed-goto" if computed_goto else "goto", "line": number})
            accept = ACCEPT_RE.search(code)
            if accept:
                accepted, accepted_indexes = _data_references(accept.group(1))
                if accepted:
                    name = accepted[0]; tainted.add(name)
                    access.append({"file": rel, "line": number, "field": name, "mode": "write", "operation": "ACCEPT"})
                    flows.append({"file": rel, "line": number, "field": name, "flow": "external-input"})
                    for index in accepted_indexes:
                        access.append({"file": rel, "line": number, "field": index, "mode": "read", "operation": "SUBSCRIPT"})
            move = MOVE_RE.search(code)
            if move:
                source_text, destination_text = move.groups()
                source_identifiers = re.sub(r"'[^']*'|\"[^\"]*\"", "", source_text)
                sources, source_indexes = _data_references(source_identifiers)
                destinations, indexes = _data_references(destination_text)
                for source in sources:
                    access.append({"file": rel, "line": number, "field": source, "mode": "read", "operation": "MOVE"})
                for index in source_indexes:
                    access.append({"file": rel, "line": number, "field": index, "mode": "read", "operation": "SUBSCRIPT"})
                for index in indexes:
                    access.append({"file": rel, "line": number, "field": index, "mode": "read", "operation": "SUBSCRIPT"})
                tainted_sources = [source for source in sources if source in tainted]
                for destination in destinations:
                    access.append({"file": rel, "line": number, "field": destination, "mode": "write", "operation": "MOVE"})
                    if tainted_sources:
                        tainted.add(destination)
                        for source in tainted_sources:
                            flows.append({"file": rel, "line": number, "from": source, "to": destination, "flow": "tainted-move"})
                    elif not conditional_assignment:
                        tainted.discard(destination)
                    for source in sources:
                        if source in layouts and destination in layouts and max(item["length"] for item in layouts[source]) > min(item["length"] for item in layouts[destination]):
                            findings.append(Finding("PC502", "high", rel, number, f"MOVE from {source} may truncate into {destination}.", "Validate size and use an explicitly compatible destination."))
            compute = COMPUTE_RE.search(code)
            if compute:
                destination_text, expression = compute.groups()
                destinations, destination_indexes = _data_references(destination_text)
                compute_sources, compute_indexes = _data_references(expression)
                if destinations:
                    destination = destinations[0]
                    access.append({"file": rel, "line": number, "field": destination, "mode": "write", "operation": "COMPUTE"})
                    for index in destination_indexes:
                        access.append({"file": rel, "line": number, "field": index, "mode": "read", "operation": "SUBSCRIPT"})
                    for source in compute_sources:
                        access.append({"file": rel, "line": number, "field": source, "mode": "read", "operation": "COMPUTE"})
                    for index in compute_indexes:
                        access.append({"file": rel, "line": number, "field": index, "mode": "read", "operation": "SUBSCRIPT"})
                    tainted_compute = [source for source in compute_sources if source in tainted]
                    if tainted_compute:
                        tainted.add(destination)
                        for source in tainted_compute:
                            flows.append({"file": rel, "line": number, "from": source, "to": destination, "flow": "tainted-compute"})
                    elif not conditional_assignment:
                        tainted.discard(destination)
            for name, subscript in SUBSCRIPT_RE.findall(code):
                name = name.upper()
                value = subscript.strip()
                definitions = layouts.get(name, [])
                statically_safe = value.isdigit() and definitions and all(1 <= int(value) <= item["occurs"] for item in definitions)
                if not statically_safe:
                    findings.append(Finding("PC501", "medium", rel, number, f"Subscripted reference {name}({value}) requires a demonstrated bounds check.", "Validate the subscript against the declared OCCURS range before access."))
            if "MOVE CORRESPONDING" in upper:
                findings.append(Finding("PC504", "medium", rel, number, "MOVE CORRESPONDING can silently change behavior when group fields evolve.", "Use explicit field moves or verify field-level change impact."))
            if tainted and ("CALL " in upper or "DIVIDE " in upper):
                used = sorted(name for name in tainted if re.search(rf"\b{re.escape(name)}\b", upper))
                if used:
                    findings.append(Finding("PC503", "high", rel, number, f"External input reaches a sensitive operation through {', '.join(used)}.", "Validate and normalize the value before arithmetic or dynamic dispatch."))
            stripped = upper.strip()
            unconditional_goto = re.match(r"^GO\s+TO\b", stripped) and not computed_goto
            if (unconditional_goto and conditional_depth == 0) or (conditional_depth == 0 and any(token in stripped for token in ("STOP RUN", "GOBACK", "EXIT PROGRAM"))):
                paragraph_terminated = True
            if "END-IF" in stripped:
                conditional_depth = max(0, conditional_depth - 1)
            if stripped.endswith("."):
                conditional_depth = 0
    return access, controls, flows, findings


def analyze_assurance(root: Path, fail_on: str = "none") -> dict[str, Any]:
    root = root.resolve()
    if fail_on not in SEVERITY_RANK:
        raise ValueError(f"Unsupported severity gate: {fail_on}")
    base = scan_project(root)
    files = _safe_files(root, SOURCE_SUFFIXES)
    programs = [path for path in files if path.suffix.lower() in {".cbl", ".cob"}]
    layouts = _field_layouts(root)
    access, control, flows, new_findings = _access_and_flow(root, programs, layouts)
    findings = list(base["findings"]) + [asdict(item) for item in new_findings]
    counts = {severity: sum(item["severity"] == severity for item in findings) for severity in ("critical", "high", "medium", "low")}
    blocked = [] if fail_on == "none" else [item for item in findings if SEVERITY_RANK[item["severity"]] <= SEVERITY_RANK[fail_on]]
    return {
        "schema": "peacobol-assurance-1",
        "project": root.name,
        "program_graph": _program_graph(root, programs),
        "copybook_graph": _copy_graph(root, files),
        "field_access": access,
        "control_flow": control,
        "data_flow": flows,
        "findings": findings,
        "summary": {"findings": counts, "field_accesses": len(access), "control_edges": len(control), "data_flows": len(flows)},
        "gate": {"threshold": fail_on, "ok": not blocked, "blocked_findings": len(blocked)},
        "ok": not blocked,
    }
