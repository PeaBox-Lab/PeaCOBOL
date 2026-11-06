from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

DECL_RE = re.compile(r"^\s*(\d{2}|77)\s+([A-Z0-9-]+)\b(.*)$", re.I)
REDEFINES_RE = re.compile(r"\bREDEFINES\s+([A-Z0-9-]+)", re.I)
OCCURS_RE = re.compile(r"\bOCCURS\s+(\d+)\s+(?:TO\s+(\d+)\s+)?TIMES\b", re.I)
PIC_RE = re.compile(r"\bPIC(?:TURE)?\s+(?:IS\s+)?([^\s.]+)", re.I)
USAGE_RE = re.compile(r"(?:\bUSAGE\s+(?:IS\s+)?)?\b(COMP(?:-[1-5])?|BINARY|PACKED-DECIMAL|DISPLAY)\b", re.I)


@dataclass
class Field:
    level: int
    name: str
    picture: str | None
    usage: str
    offset: int = 0
    length: int = 0
    total_length: int = 0
    occurs: int = 1
    occurs_min: int = 1
    redefines: str | None = None
    parent: str | None = None
    line: int = 0
    children: list["Field"] = field(default_factory=list)

    @property
    def elementary(self) -> bool:
        return self.picture is not None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _expanded_count(pic: str, symbols: set[str]) -> int:
    pic = pic.upper()
    total = 0
    i = 0
    while i < len(pic):
        ch = pic[i]
        if ch in symbols:
            repeat = 1
            if i + 1 < len(pic) and pic[i + 1] == "(":
                end = pic.find(")", i + 2)
                if end != -1 and pic[i + 2:end].isdigit():
                    repeat = int(pic[i + 2:end])
                    i = end
            total += repeat
        i += 1
    if "CR" in pic:
        total += 2
    if "DB" in pic:
        total += 2
    return total


def picture_digits(pic: str) -> int:
    return _expanded_count(pic, {"9", "Z", "*", "P"})


def display_length(pic: str) -> int:
    # S, V and P are non-storage symbols; edited characters occupy storage.
    return _expanded_count(pic, {"X", "A", "9", "Z", "*", "0", "B", "/", ",", ".", "+", "-"})


def storage_length(pic: str, usage: str) -> int:
    digits = picture_digits(pic)
    u = (usage or "DISPLAY").upper()
    if u in ("COMP-3", "PACKED-DECIMAL"):
        return (digits + 2) // 2
    if u in ("COMP", "COMP-4", "BINARY", "COMP-5"):
        return 2 if digits <= 4 else 4 if digits <= 9 else 8
    if u == "COMP-1":
        return 4
    if u == "COMP-2":
        return 8
    return display_length(pic)


def _logical_lines(path: Path) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    pending = ""
    start = 0
    for number, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if len(raw) >= 7 and raw[6] in ("*", "/"):
            continue
        text = raw[6:] if len(raw) >= 7 and raw[:6].strip().isdigit() else raw
        text = text.strip()
        if not text:
            continue
        if not pending:
            start = number
        pending = f"{pending} {text}".strip()
        if text.endswith("."):
            lines.append((start, pending))
            pending = ""
    if pending:
        lines.append((start, pending))
    return lines


def parse_copybook(path: Path) -> list[Field]:
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Copybook not found: {path}")
    roots: list[Field] = []
    stack: list[Field] = []
    for line_number, statement in _logical_lines(path):
        m = DECL_RE.match(statement)
        if not m:
            continue
        level, name, tail = m.groups()
        level_i = int(level)
        if level_i in (66, 88):
            continue
        redef_m = REDEFINES_RE.search(tail)
        occurs_m = OCCURS_RE.search(tail)
        pic_m = PIC_RE.search(tail)
        usage_m = USAGE_RE.search(tail)
        occurs_min = int(occurs_m.group(1)) if occurs_m else 1
        occurs = int(occurs_m.group(2) or occurs_m.group(1)) if occurs_m else 1
        node = Field(
            level=level_i,
            name=name.upper(),
            picture=pic_m.group(1).upper() if pic_m else None,
            usage=(usage_m.group(1) if usage_m else "DISPLAY").upper(),
            occurs=occurs,
            occurs_min=occurs_min,
            redefines=redef_m.group(1).upper() if redef_m else None,
            line=line_number,
        )
        while stack and stack[-1].level >= level_i:
            stack.pop()
        if stack and level_i != 77:
            node.parent = stack[-1].name
            stack[-1].children.append(node)
        else:
            roots.append(node)
        stack.append(node)
    _layout_siblings(roots, 0)
    return roots


def _layout_siblings(nodes: list[Field], start: int) -> int:
    cursor = start
    extent = start
    by_name: dict[str, Field] = {}
    for node in nodes:
        if node.redefines:
            target = by_name.get(node.redefines)
            if target is None:
                raise ValueError(f"Line {node.line}: REDEFINES target {node.redefines} was not found among prior siblings")
            node.offset = target.offset
        else:
            node.offset = cursor
        if node.elementary:
            node.length = storage_length(node.picture or "", node.usage)
        else:
            child_end = _layout_siblings(node.children, node.offset)
            node.length = child_end - node.offset
        node.total_length = node.length * node.occurs
        node_end = node.offset + node.total_length
        extent = max(extent, node_end)
        if not node.redefines:
            cursor = node_end
        else:
            cursor = max(cursor, node_end)
        by_name[node.name] = node
    return max(cursor, extent)


def record_length(fields: list[Field]) -> int:
    return max((f.offset + f.total_length for f in fields), default=0)


def flatten_fields(fields: list[Field]) -> list[Field]:
    out: list[Field] = []
    for item in fields:
        out.append(item)
        out.extend(flatten_fields(item.children))
    return out
