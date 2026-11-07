from __future__ import annotations
import csv
import json
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any
from .copybook import Field, record_length
VALID_ENCODINGS = {"ascii", "utf-8", "cp037", "cp500"}
def unpack_comp3(data: bytes, scale: int = 0) -> Decimal:
    if not data:
        raise ValueError("COMP-3 data is empty")
    nibbles: list[int] = []
    for byte in data:
        nibbles.extend((byte >> 4, byte & 0x0F))
    sign_nibble = nibbles.pop()
    if sign_nibble not in (0xA, 0xB, 0xC, 0xD, 0xE, 0xF):
        raise ValueError(f"Invalid COMP-3 sign nibble: {sign_nibble:X}")
    if any(x > 9 for x in nibbles):
        raise ValueError("Invalid decimal digit in COMP-3 data")
    number = Decimal("".join(str(x) for x in nibbles) or "0")
    if scale:
        number = number.scaleb(-scale)
    if sign_nibble in (0xB, 0xD):
        number = -number
    return number
def pack_comp3(value: Decimal | str | int, digits: int, scale: int = 0) -> bytes:
    value = Decimal(str(value))
    negative = value < 0
    scaled = int(abs(value).scaleb(scale))
    text = f"{scaled:0{digits}d}"
    if len(text) > digits:
        raise ValueError(f"Value exceeds {digits} digits")
    nibbles = [int(x) for x in text] + ([0xD] if negative else [0xC])
    if len(nibbles) % 2:
        nibbles.insert(0, 0)
    return bytes((nibbles[i] << 4) | nibbles[i + 1] for i in range(0, len(nibbles), 2))
def _scale(pic: str | None) -> int:
    if not pic or "V" not in pic.upper():
        return 0
    right = pic.upper().split("V", 1)[1]
    from .copybook import picture_digits
    return picture_digits(right)
def _decode_element(field: Field, raw: bytes, encoding: str, binary_byteorder: str, binary_signed: bool) -> Any:
    usage = field.usage.upper()
    if usage in ("COMP-3", "PACKED-DECIMAL"):
        return str(unpack_comp3(raw, _scale(field.picture)))
    if usage in ("COMP", "COMP-4", "BINARY", "COMP-5"):
        return int.from_bytes(raw, byteorder=binary_byteorder, signed=binary_signed)
    text = raw.decode(encoding, errors="replace")
    pic = (field.picture or "").upper()
    if "9" in pic and "X" not in pic and "A" not in pic:
        cleaned = text.strip().replace(",", "")
        if cleaned and cleaned.lstrip("+-").isdigit():
            value = Decimal(cleaned)
            scale = _scale(pic)
            if scale:
                value = value.scaleb(-scale)
            return str(value)
    return text.rstrip()
def _decode_nodes(nodes: list[Field], data: bytes, encoding: str, binary_byteorder: str, binary_signed: bool, shift: int = 0) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for node in nodes:
        values: list[Any] = []
        for index in range(node.occurs):
            base = node.offset + shift + index * node.length
            if node.children:
                child_shift = base - node.offset
                value = _decode_nodes(node.children, data, encoding, binary_byteorder, binary_signed, child_shift)
            else:
                value = _decode_element(node, data[base:base + node.length], encoding, binary_byteorder, binary_signed)
            values.append(value)
        result[node.name] = values if node.occurs > 1 else values[0]
    return result
def decode_record(fields: list[Field], data: bytes, encoding: str = "ascii", binary_byteorder: str = "big", binary_signed: bool = True) -> dict[str, Any]:
    if encoding not in VALID_ENCODINGS:
        raise ValueError(f"Unsupported encoding: {encoding}")
    if binary_byteorder not in {"big", "little"}:
        raise ValueError("Binary byte order must be big or little")
    expected = record_length(fields)
    if len(data) != expected:
        raise ValueError(f"Record length is {len(data)} bytes; copybook requires {expected}")
    return _decode_nodes(fields, data, encoding, binary_byteorder, binary_signed)
def hex_view(data: bytes, width: int = 16) -> list[dict[str, str]]:
    if width < 4 or width > 64:
        raise ValueError("Hex width must be between 4 and 64")
    rows = []
    for offset in range(0, len(data), width):
        chunk = data[offset:offset + width]
        rows.append({
            "offset": f"{offset:08X}",
            "hex": " ".join(f"{x:02X}" for x in chunk),
            "ascii": "".join(chr(x) if 32 <= x <= 126 else "." for x in chunk),
        })
    return rows
def convert_records(copybook_fields: list[Field], source: Path, encoding: str, output_format: str, binary_byteorder: str = "big", binary_signed: bool = True) -> str:
    data = source.read_bytes()
    length = record_length(copybook_fields)
    if length <= 0:
        raise ValueError("Copybook has no storage fields")
    if len(data) % length:
        raise ValueError(f"Input size {len(data)} is not a multiple of record length {length}")
    records = [decode_record(copybook_fields, data[i:i + length], encoding, binary_byteorder, binary_signed) for i in range(0, len(data), length)]
    if output_format == "jsonl":
        return "\n".join(json.dumps(x, sort_keys=True) for x in records) + ("\n" if records else "")
    if output_format != "csv":
        raise ValueError(f"Unsupported output format: {output_format}")
    if any(any(isinstance(v, (dict, list)) for v in row.values()) for row in records):
        raise ValueError("CSV export supports flat copybooks only; use JSONL for groups or OCCURS")
    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(records[0]) if records else [])
    if records:
        writer.writeheader()
        writer.writerows(records)
    return stream.getvalue()
