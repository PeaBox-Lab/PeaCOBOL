from __future__ import annotations

import hashlib
import json
import os
import stat
from decimal import Decimal
from pathlib import Path
from typing import Any

MAX_GOLDEN_BYTES = 64 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024

from .copybook import Field, flatten_fields, parse_copybook, picture_digits, record_length
from .records import pack_comp3


def _scale(pic: str | None) -> int:
    if not pic or "V" not in pic.upper():
        return 0
    return picture_digits(pic.upper().split("V", 1)[1])


def _display_bytes(field: Field, value: str, encoding: str) -> bytes:
    text = value
    pic = (field.picture or "").upper()
    if "9" in pic and "X" not in pic and "A" not in pic:
        digits = picture_digits(pic)
        decimal = Decimal(value)
        scaled = int(abs(decimal).scaleb(_scale(pic)))
        text = f"{scaled:0{digits}d}"
        if "S" in pic and decimal < 0 and text:
            negative_overpunch = {"0": "}", "1": "J", "2": "K", "3": "L", "4": "M", "5": "N", "6": "O", "7": "P", "8": "Q", "9": "R"}
            text = text[:-1] + negative_overpunch[text[-1]]
    return text.encode(encoding)[:field.length].ljust(field.length, b" ")


def _field_value(field: Field, variant: str) -> Any:
    pic = (field.picture or "").upper()
    numeric = "9" in pic and "X" not in pic and "A" not in pic
    if numeric:
        digits = picture_digits(pic)
        scale = _scale(pic)
        whole = "9" * max(1, digits - scale)
        fraction = "9" * scale
        maximum = whole + ("." + fraction if scale else "")
        if variant == "minimum":
            return "-" + maximum if "S" in pic else "0"
        if variant == "maximum":
            return maximum
        if variant == "invalid":
            return "invalid-numeric"
        return "1" if not scale else "0." + "0" * (scale - 1) + "1"
    if variant == "minimum":
        return ""
    if variant == "maximum":
        return "X" * field.length
    if variant == "invalid":
        return "\x00" * field.length
    return "A" * min(field.length, 1)


def _encode_element(field: Field, value: Any, encoding: str, byteorder: str, signed: bool) -> bytes:
    usage = field.usage.upper()
    if usage in ("COMP-3", "PACKED-DECIMAL"):
        if value == "invalid-numeric":
            return bytes([0xFF]) * field.length
        return pack_comp3(value, picture_digits(field.picture or ""), _scale(field.picture))
    if usage in ("COMP", "COMP-4", "BINARY", "COMP-5"):
        if value == "invalid-numeric":
            return bytes([0xFF]) * field.length
        decimal = Decimal(str(value))
        scaled = decimal.scaleb(_scale(field.picture))
        if scaled != scaled.to_integral_value():
            raise ValueError(f"Value cannot be represented exactly for {field.name}")
        integer = int(scaled)
        minimum = -(1 << (field.length * 8 - 1)) if signed else 0
        maximum = (1 << (field.length * 8 - (1 if signed else 0))) - 1
        if integer < minimum or integer > maximum:
            raise ValueError(f"Value is outside binary range for {field.name}")
        return integer.to_bytes(field.length, byteorder=byteorder, signed=signed)
    if value == "invalid-numeric":
        return ("X" * field.length).encode(encoding)
    return _display_bytes(field, str(value), encoding)


def _build_nodes(nodes: list[Field], variant: str, data: bytearray, encoding: str, byteorder: str, signed: bool, shift: int = 0) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for node in nodes:
        occurrences = []
        for index in range(node.occurs):
            base = node.offset + shift + index * node.length
            if node.children:
                value = _build_nodes(node.children, variant, data, encoding, byteorder, signed, base - node.offset)
            else:
                value = _field_value(node, variant)
                data[base:base + node.length] = _encode_element(node, value, encoding, byteorder, signed)
            occurrences.append(value)
        values[node.name] = occurrences if node.occurs > 1 else occurrences[0]
    return values


def generate_cases(copybook: Path, encoding: str = "ascii", byteorder: str = "big", signed: bool = True) -> dict[str, Any]:
    copybook = copybook.resolve()
    fields = parse_copybook(copybook)
    length = record_length(fields)
    cases = []
    for variant in ("typical", "minimum", "maximum", "invalid"):
        data = bytearray(length)
        values = _build_nodes(fields, variant, data, encoding, byteorder, signed)
        cases.append({"id": variant, "valid": variant != "invalid", "record_hex": bytes(data).hex().upper(), "values": values})
    payload = {
        "schema": "peacobol-test-cases-1",
        "copybook": copybook.name,
        "copybook_sha256": hashlib.sha256(copybook.read_bytes()).hexdigest(),
        "record_length": length,
        "encoding": encoding,
        "binary_byteorder": byteorder,
        "binary_signed": signed,
        "fields": len(flatten_fields(fields)),
        "cases": cases,
    }
    payload["cases_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    return payload


def cobol_check_stub(program: str, cases: dict[str, Any]) -> str:
    name = program.upper()
    if not name.replace("-", "").isalnum() or len(name) > 22:
        raise ValueError("Invalid COBOL program name")
    length = cases["record_length"]
    lines = [
        "       IDENTIFICATION DIVISION.",
        f"       PROGRAM-ID. {name}-TEST.",
        "       DATA DIVISION.",
        "       WORKING-STORAGE SECTION.",
        f"       01 TEST-RECORD PIC X({length}).",
        "       01 TEST-RESULT PIC X VALUE 'P'.",
        "       PROCEDURE DIVISION.",
        "       TEST-SUITE.",
    ]
    for case in cases["cases"]:
        paragraph = f"TEST-{case['id'].upper()}"
        lines.append(f"           PERFORM {paragraph}")
    lines.extend(["           GOBACK.", ""])
    for case in cases["cases"]:
        paragraph = f"TEST-{case['id'].upper()}"
        lines.extend([
            f"       {paragraph}.",
            f"      * COBOL Check case scaffold: {case['id']}",
            f"           MOVE X'{case['record_hex']}' TO TEST-RECORD",
            f"           CALL '{name}' USING TEST-RECORD",
            "      * Add COBOL Check EXPECT/assertion for TEST-RESULT here.",
            f"           DISPLAY 'CASE {case['id'].upper()} RESULT ' TEST-RESULT",
            "           EXIT.",
            "",
        ])
    return "\n".join(lines)


def _open_bounded(path: Path):
    if path.is_symlink():
        raise FileNotFoundError(f"Golden file not found: {path}")
    absolute = Path(os.path.abspath(os.fspath(path)))
    descriptor = os.open(absolute, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    file_stat = os.fstat(descriptor)
    if not stat.S_ISREG(file_stat.st_mode):
        os.close(descriptor)
        raise FileNotFoundError(f"Golden file not found: {path}")
    if file_stat.st_size > MAX_GOLDEN_BYTES:
        os.close(descriptor)
        raise ValueError(f"Golden file exceeds {MAX_GOLDEN_BYTES} bytes")
    return absolute, descriptor, file_stat.st_size


def compare_golden(actual: Path, expected: Path) -> dict[str, Any]:
    actual_path, actual_fd, actual_size = _open_bounded(actual)
    try:
        expected_path, expected_fd, expected_size = _open_bounded(expected)
    except Exception:
        os.close(actual_fd)
        raise
    actual_hash = hashlib.sha256(); expected_hash = hashlib.sha256(); first_difference = None; offset = 0
    try:
        with os.fdopen(actual_fd, "rb") as left, os.fdopen(expected_fd, "rb") as right:
            while True:
                left_chunk = left.read(CHUNK_SIZE); right_chunk = right.read(CHUNK_SIZE)
                if offset + len(left_chunk) > MAX_GOLDEN_BYTES or offset + len(right_chunk) > MAX_GOLDEN_BYTES:
                    raise ValueError(f"Golden file exceeds {MAX_GOLDEN_BYTES} bytes")
                actual_hash.update(left_chunk); expected_hash.update(right_chunk)
                shared = min(len(left_chunk), len(right_chunk))
                if first_difference is None and left_chunk[:shared] != right_chunk[:shared]:
                    first_difference = offset + next(index for index in range(shared) if left_chunk[index] != right_chunk[index])
                if first_difference is None and len(left_chunk) != len(right_chunk):
                    first_difference = offset + shared
                if not left_chunk and not right_chunk:
                    break
                offset += max(len(left_chunk), len(right_chunk))
    except Exception:
        raise
    return {
        "schema": "peacobol-golden-1",
        "ok": first_difference is None,
        "actual": {"file": actual_path.name, "bytes": actual_size, "sha256": actual_hash.hexdigest()},
        "expected": {"file": expected_path.name, "bytes": expected_size, "sha256": expected_hash.hexdigest()},
        "first_difference": first_difference,
        "length_delta": actual_size - expected_size,
    }
