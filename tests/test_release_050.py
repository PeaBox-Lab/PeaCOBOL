import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from peacobol.assurance import analyze_assurance
from peacobol.audit import append_event, verify_log
from peacobol.core import build
from peacobol.impact import compare_copybooks
from peacobol.profiles import load_profile
from peacobol.sarif import to_sarif


def _audit_worker(path, count):
    for index in range(count):
        append_event(Path(path), "worker", str(index), "success")


class AssuranceTests(unittest.TestCase):
    def _project(self, directory):
        root = Path(directory)
        (root / "src").mkdir()
        (root / "copybooks").mkdir()
        (root / "copybooks" / "DATA.cpy").write_text("01 DATA-REC.\n 05 LARGE PIC X(10).\n 05 SMALL PIC X(3).\n 05 ITEMS OCCURS 3 TIMES PIC X.\n", encoding="utf-8")
        (root / "copybooks" / "NESTED.cpy").write_text(" COPY DATA.\n", encoding="utf-8")
        (root / "src" / "MAIN.cbl").write_text("""       IDENTIFICATION DIVISION.
       PROGRAM-ID. MAIN.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY DATA.
       PROCEDURE DIVISION.
       START-PARA.
           ACCEPT LARGE
           MOVE LARGE TO SMALL
           MOVE CORRESPONDING DATA-REC TO DATA-REC
           DISPLAY ITEMS(WS-IDX)
           CALL 'SUBPROG'
           PERFORM END-PARA
       END-PARA.
           GOBACK.
""", encoding="utf-8")
        (root / "src" / "SUB.cbl").write_text("       IDENTIFICATION DIVISION.\n       PROGRAM-ID. SUBPROG.\n       PROCEDURE DIVISION.\n           GOBACK.\n", encoding="utf-8")
        return root

    def test_graphs_access_flow_and_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            report = analyze_assurance(self._project(directory))
            edge = report["program_graph"]["edges"][0]
            self.assertEqual((edge["from"], edge["to"], edge["resolved"]), ("MAIN", "SUBPROG", True))
            self.assertTrue(any(edge["copybook"] == "DATA" and edge["resolved"] for edge in report["copybook_graph"]["edges"]))
            self.assertTrue(any(item["field"] == "LARGE" and item["mode"] == "write" for item in report["field_access"]))
            self.assertTrue(any(item["type"] == "perform" for item in report["control_flow"]))
            rules = {item["rule"] for item in report["findings"]}
            self.assertTrue({"PC501", "PC502", "PC504"}.issubset(rules))

    def test_severity_gate_blocks_at_high(self):
        with tempfile.TemporaryDirectory() as directory:
            report = analyze_assurance(self._project(directory), "high")
            self.assertFalse(report["ok"])
            self.assertGreater(report["gate"]["blocked_findings"], 0)

    def test_none_gate_always_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(analyze_assurance(self._project(directory), "none")["ok"])

    def test_move_tracks_all_destinations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(directory)
            path = root / "src" / "MAIN.cbl"
            path.write_text(path.read_text(encoding="utf-8").replace("MOVE LARGE TO SMALL", "MOVE LARGE TO SMALL ITEMS"), encoding="utf-8")
            report = analyze_assurance(root)
            writes = {item["field"] for item in report["field_access"] if item["mode"] == "write" and item["operation"] == "MOVE"}
            self.assertTrue({"SMALL", "ITEMS"}.issubset(writes))
            truncation_targets = {item["message"].split()[-1].rstrip(".") for item in report["findings"] if item["rule"] == "PC502"}
            self.assertTrue({"SMALL", "ITEMS"}.issubset(truncation_targets))

    def test_safe_constant_subscript_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(directory)
            path = root / "src" / "MAIN.cbl"
            path.write_text(path.read_text(encoding="utf-8").replace("ITEMS(WS-IDX)", "ITEMS(2)"), encoding="utf-8")
            report = analyze_assurance(root)
            self.assertFalse(any(item["rule"] == "PC501" for item in report["findings"]))

    def test_trusted_overwrite_kills_taint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(directory)
            path = root / "src" / "MAIN.cbl"
            text = path.read_text(encoding="utf-8").replace("MOVE LARGE TO SMALL", "MOVE 'SAFE' TO LARGE\n           DIVIDE SMALL BY LARGE")
            path.write_text(text, encoding="utf-8")
            report = analyze_assurance(root)
            self.assertFalse(any(item["rule"] == "PC503" for item in report["findings"]))

    def test_unconditional_transfer_suppresses_fallthrough(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(directory)
            path = root / "src" / "MAIN.cbl"
            text = path.read_text(encoding="utf-8").replace("PERFORM END-PARA", "GO TO END-PARA\n       MID-PARA.\n           DISPLAY 'NO FALLTHROUGH'")
            path.write_text(text, encoding="utf-8")
            report = analyze_assurance(root)
            self.assertFalse(any(item["type"] == "fallthrough" and item["from"] == "START-PARA" and item["to"] == "MID-PARA" for item in report["control_flow"]))

    def test_conditional_overwrite_does_not_kill_taint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(directory)
            path = root / "src" / "MAIN.cbl"
            text = path.read_text(encoding="utf-8").replace("MOVE LARGE TO SMALL", "IF SMALL = 'Y'\n               MOVE 'SAFE' TO LARGE\n           END-IF\n           DIVIDE SMALL BY LARGE")
            path.write_text(text, encoding="utf-8")
            report = analyze_assurance(root)
            self.assertTrue(any(item["rule"] == "PC503" for item in report["findings"]))

    def test_destination_indexes_are_reads_not_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(directory)
            path = root / "src" / "MAIN.cbl"
            text = path.read_text(encoding="utf-8").replace("MOVE LARGE TO SMALL", "MOVE LARGE TO ITEMS(WS-IDX)")
            path.write_text(text, encoding="utf-8")
            report = analyze_assurance(root)
            self.assertTrue(any(item["field"] == "ITEMS" and item["mode"] == "write" for item in report["field_access"]))
            self.assertTrue(any(item["field"] == "WS-IDX" and item["mode"] == "read" for item in report["field_access"]))
            self.assertFalse(any(item["field"] == "WS-IDX" and item["mode"] == "write" for item in report["field_access"]))

    def test_computed_goto_preserves_fallthrough(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(directory)
            path = root / "src" / "MAIN.cbl"
            text = path.read_text(encoding="utf-8").replace("PERFORM END-PARA", "GO TO END-PARA DEPENDING ON SMALL\n       MID-PARA.\n           DISPLAY 'FALLTHROUGH POSSIBLE'")
            path.write_text(text, encoding="utf-8")
            report = analyze_assurance(root)
            self.assertTrue(any(item["type"] == "fallthrough" and item["from"] == "START-PARA" and item["to"] == "MID-PARA" for item in report["control_flow"]))

    def test_conditional_goto_preserves_fallthrough(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(directory)
            path = root / "src" / "MAIN.cbl"
            text = path.read_text(encoding="utf-8").replace("PERFORM END-PARA", "IF SMALL = 'Y'\n               GO TO END-PARA\n           END-IF\n       MID-PARA.\n           DISPLAY 'FALLTHROUGH POSSIBLE'")
            path.write_text(text, encoding="utf-8")
            report = analyze_assurance(root)
            self.assertTrue(any(item["type"] == "fallthrough" and item["from"] == "START-PARA" and item["to"] == "MID-PARA" for item in report["control_flow"]))

    def test_qualified_fields_keep_distinct_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "src").mkdir(); (root / "copybooks").mkdir()
            (root / "copybooks" / "Q.cpy").write_text("01 REC.\n 05 INPUT-REC.\n  10 STATUS PIC X(10).\n 05 OUTPUT-REC.\n  10 STATUS PIC X(3).\n", encoding="utf-8")
            (root / "src" / "Q.cbl").write_text("       IDENTIFICATION DIVISION.\n       PROGRAM-ID. Q.\n       PROCEDURE DIVISION.\n           ACCEPT STATUS OF INPUT-REC\n           MOVE STATUS OF INPUT-REC TO STATUS OF OUTPUT-REC\n           GOBACK.\n", encoding="utf-8")
            report = analyze_assurance(root)
            fields = {item["field"] for item in report["field_access"]}
            self.assertIn("STATUS OF INPUT-REC", fields)
            self.assertIn("STATUS OF OUTPUT-REC", fields)
            self.assertTrue(any(item["rule"] == "PC502" and "STATUS OF OUTPUT-REC" in item["message"] for item in report["findings"]))

    def test_period_terminated_if_resets_condition_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(directory)
            path = root / "src" / "MAIN.cbl"
            text = path.read_text(encoding="utf-8").replace("PERFORM END-PARA", "IF SMALL = 'Y'\n               DISPLAY SMALL.\n           GO TO END-PARA\n       MID-PARA.\n           DISPLAY 'UNREACHABLE'")
            path.write_text(text, encoding="utf-8")
            report = analyze_assurance(root)
            self.assertFalse(any(item["type"] == "fallthrough" and item["from"] == "START-PARA" and item["to"] == "MID-PARA" for item in report["control_flow"]))

    def test_computed_goto_records_all_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(directory)
            path = root / "src" / "MAIN.cbl"
            text = path.read_text(encoding="utf-8").replace("PERFORM END-PARA", "GO TO MID-PARA END-PARA DEPENDING ON SMALL\n       MID-PARA.\n           DISPLAY 'POSSIBLE'")
            path.write_text(text, encoding="utf-8")
            report = analyze_assurance(root)
            targets = {item["to"] for item in report["control_flow"] if item["type"] == "computed-goto"}
            self.assertEqual(targets, {"MID-PARA", "END-PARA"})

    def test_compute_preserves_qualified_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "src").mkdir(); (root / "copybooks").mkdir()
            (root / "copybooks" / "Q.cpy").write_text("01 REC.\n 05 IN-REC.\n  10 AMOUNT PIC 9(3).\n 05 OUT-REC.\n  10 RESULT PIC 9(4).\n", encoding="utf-8")
            (root / "src" / "Q.cbl").write_text("       IDENTIFICATION DIVISION.\n       PROGRAM-ID. Q.\n       PROCEDURE DIVISION.\n           COMPUTE RESULT OF OUT-REC = AMOUNT OF IN-REC + 1\n           GOBACK.\n", encoding="utf-8")
            report = analyze_assurance(root)
            self.assertTrue(any(item["field"] == "RESULT OF OUT-REC" and item["mode"] == "write" for item in report["field_access"]))
            self.assertTrue(any(item["field"] == "AMOUNT OF IN-REC" and item["mode"] == "read" for item in report["field_access"]))


class ProfileHardeningTests(unittest.TestCase):
    def test_release_policy_cannot_be_weakened(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "peacobol.json").write_text(json.dumps({"profiles": {"release": {"policy": {"max_findings": {"high": None}, "fail_on_build_warning": False, "require_evidence": False}}}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_profile(root, "release")

    def test_release_policy_can_be_strengthened(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "peacobol.json").write_text(json.dumps({"profiles": {"release": {"policy": {"max_findings": {"medium": 0}}}}}), encoding="utf-8")
            profile = load_profile(root, "release")
            self.assertEqual(profile["policy"]["max_findings"]["medium"], 0)


class ImpactTests(unittest.TestCase):
    def test_field_changes_and_hash_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "old.cpy"; new = root / "new.cpy"
            old.write_text("01 REC.\n 05 CODE PIC X(3).\n 05 AMOUNT PIC 9(3).\n", encoding="utf-8")
            new.write_text("01 REC.\n 05 CODE PIC X(5).\n 05 AMOUNT PIC 9(3).\n 05 STATUS PIC X.\n", encoding="utf-8")
            result = compare_copybooks(old, new)
            self.assertFalse(result["compatible"])
            self.assertEqual(result["record_length_delta"], 3)
            self.assertGreaterEqual(result["summary"]["breaking"], 1)
            self.assertEqual(len(result["impact_hash"]), 64)
            self.assertTrue(any(item["path"] == "REC.CODE" and item["change"] == "modified" for item in result["changes"]))

    def test_identical_copybooks_are_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "a.cpy"; second = root / "b.cpy"
            text = "01 REC.\n 05 CODE PIC X(3).\n"
            first.write_text(text, encoding="utf-8"); second.write_text(text, encoding="utf-8")
            result = compare_copybooks(first, second)
            self.assertTrue(result["compatible"])
            self.assertFalse(result["changes"])


class IntegrityHardeningTests(unittest.TestCase):
    @patch("peacobol.core.shutil.which", return_value="/usr/bin/cobc")
    def test_symlinked_build_directory_is_rejected(self, _):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (root / "A.cbl").write_text("       PROGRAM-ID. A.\n", encoding="utf-8")
            try:
                (root / "build").symlink_to(Path(outside), target_is_directory=True)
            except OSError:
                self.skipTest("Symlinks are unavailable")
            with self.assertRaises(ValueError):
                build(root)

    def test_concurrent_audit_writers_preserve_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "audit.jsonl"
            processes = [multiprocessing.Process(target=_audit_worker, args=(str(log), 5)) for _ in range(3)]
            for process in processes:
                process.start()
            for process in processes:
                process.join(10)
                self.assertEqual(process.exitcode, 0)
            result = verify_log(log)
            self.assertTrue(result["ok"])
            self.assertEqual(result["events"], 15)

    def test_audit_verification_is_safe_during_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "audit.jsonl"
            append_event(log, "initial", "0", "success")
            process = multiprocessing.Process(target=_audit_worker, args=(str(log), 20))
            process.start()
            while process.is_alive():
                self.assertTrue(verify_log(log)["ok"])
            process.join(10)
            self.assertEqual(process.exitcode, 0)
            result = verify_log(log)
            self.assertTrue(result["ok"])
            self.assertEqual(result["events"], 21)


class SarifTests(unittest.TestCase):
    def test_sarif_contains_rules_results_and_gate(self):
        report = {"schema": "peacobol-assurance-1", "project": "p", "gate": {"ok": False}, "findings": [{"rule": "PC501", "severity": "medium", "file": "A.cbl", "line": 4, "message": "Bounds", "remediation": "Validate"}]}
        result = to_sarif(report)
        self.assertEqual(result["version"], "2.1.0")
        run = result["runs"][0]
        self.assertEqual(run["results"][0]["level"], "warning")
        self.assertEqual(run["tool"]["driver"]["rules"][0]["id"], "PC501")
        self.assertFalse(run["properties"]["gate"]["ok"])


if __name__ == "__main__":
    unittest.main()
