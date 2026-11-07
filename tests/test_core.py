import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from peacobol.audit import append_event, verify_log
from peacobol.copybook import parse_copybook, record_length, storage_length
from peacobol.core import build, create_project, evidence, scan_project
from peacobol.records import decode_record, hex_view, pack_comp3, unpack_comp3
class CopybookTests(unittest.TestCase):
    def test_storage_lengths(self):
        self.assertEqual(storage_length("S9(7)V99", "COMP-3"), 5)
        self.assertEqual(storage_length("X(12)", "DISPLAY"), 12)
        self.assertEqual(storage_length("S9(9)", "BINARY"), 4)
        self.assertEqual(storage_length("ZZ,ZZ9.99-", "DISPLAY"), 10)
    def test_nested_occurs_and_redefines_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "A.cpy"
            path.write_text("""       01 REC.\n          05 ITEMS OCCURS 3 TIMES.\n             10 CODE PIC X(2).\n          05 BASE PIC X(4).\n          05 ALT REDEFINES BASE PIC X(8).\n          05 TAIL PIC X.\n""", encoding="utf-8")
            roots = parse_copybook(path)
            rec = roots[0]
            self.assertEqual(rec.children[0].total_length, 6)
            self.assertEqual(rec.children[1].offset, 6)
            self.assertEqual(rec.children[2].offset, 6)
            self.assertEqual(rec.children[3].offset, 14)
            self.assertEqual(record_length(roots), 15)
    def test_invalid_redefines_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "A.cpy"
            path.write_text("05 B REDEFINES MISSING PIC X.", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_copybook(path)
class RecordTests(unittest.TestCase):
    def test_comp3_round_trip(self):
        for value in ("123.45", "-123.45", "0"):
            packed = pack_comp3(value, 5, 2)
            self.assertEqual(unpack_comp3(packed, 2), Decimal(value))
    def test_invalid_comp3_is_rejected(self):
        with self.assertRaises(ValueError):
            unpack_comp3(bytes.fromhex("1A2C"))
    def test_decode_ascii_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "A.cpy"
            path.write_text("01 REC.\n 05 CODE PIC X(3).\n 05 AMOUNT PIC 9(3)V99.\n", encoding="utf-8")
            result = decode_record(parse_copybook(path), b"ABC12345")
            self.assertEqual(result["REC"]["CODE"], "ABC")
            self.assertEqual(result["REC"]["AMOUNT"], "123.45")
    def test_decode_requires_exact_length(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "A.cpy"
            path.write_text("01 REC.\n 05 CODE PIC X(3).\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                decode_record(parse_copybook(path), b"AB")
    def test_hex_view_is_bounded_by_width(self):
        rows = hex_view(b"ABCDEF", 4)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["offset"], "00000000")
class AnalysisTests(unittest.TestCase):
    def test_scan_and_rule_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A.cbl").write_text(" CALL 'B'\n DIVIDE A BY B\n GO TO END-X\n", encoding="utf-8")
            report = scan_project(root)
            self.assertEqual(report["calls"][0]["to"], "B")
            self.assertTrue(any(x["rule"] == "PC201" for x in report["findings"]))
    def test_comments_do_not_create_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A.cbl").write_text("      * GO TO BAD\n       PROCEDURE DIVISION.\n           GOBACK.\n", encoding="utf-8")
            self.assertFalse(scan_project(root)["findings"])
    def test_generated_directories_and_symlinks_are_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "build").mkdir()
            (root / "build" / "X.cbl").write_text("GO TO X", encoding="utf-8")
            outside = root.parent / "outside.cbl"
            outside.write_text("GO TO X", encoding="utf-8")
            link = root / "link.cbl"
            try:
                link.symlink_to(outside)
                self.assertEqual(scan_project(root)["programs"], [])
            finally:
                outside.unlink(missing_ok=True)
    def test_evidence_is_reproducible_and_excludes_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A.cbl").write_text("GOBACK.\n", encoding="utf-8")
            output = root / "evidence.json"
            first = evidence(root, exclude=[output])
            output.write_text(json.dumps(first), encoding="utf-8")
            second = evidence(root, exclude=[output])
            self.assertEqual(first, second)
            self.assertNotIn("evidence.json", second["source_hashes"])
    def test_create_project_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, "project")
            hello = root / "src" / "HELLO.cbl"
            hello.write_text("CUSTOM", encoding="utf-8")
            create_project(root, "project")
            self.assertEqual(hello.read_text(encoding="utf-8"), "CUSTOM")
class BuildTests(unittest.TestCase):
    @patch("peacobol.core.shutil.which", return_value=None)
    def test_missing_compiler_is_clear(self, _):
        with tempfile.TemporaryDirectory() as directory:
            result = build(Path(directory))
            self.assertFalse(result["ok"])
            self.assertIn("not found", result["message"])
class AuditTests(unittest.TestCase):
    def test_hash_chain_verifies(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            append_event(path, "scan", "p", "success")
            append_event(path, "build", "p", "failure")
            result = verify_log(path)
            self.assertTrue(result["ok"])
            self.assertEqual(result["events"], 2)
    def test_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            append_event(path, "scan", "p", "success")
            path.write_text(path.read_text(encoding="utf-8").replace('"success"', '"failure"'), encoding="utf-8")
            self.assertFalse(verify_log(path)["ok"])
if __name__ == "__main__":
    unittest.main()
