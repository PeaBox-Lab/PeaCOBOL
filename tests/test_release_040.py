import json
import tempfile
import unittest
from pathlib import Path
from peacobol.audit import append_event, verify_log
from peacobol.investigation import diagnose, failure_bundle
from peacobol.knowledge import list_knowledge, load_catalog, lookup
from peacobol.profiles import load_profile
from peacobol.spool import MAX_SPOOL_BYTES, parse_spool
SPOOL = """IEF142I JOB1 COMPILE - STEP WAS EXECUTED - COND CODE 0012
src/PAYMENT.cbl:7: error: invalid statement
FILE-STATUS=35
ABEND CODE S0C7
"""
class SpoolTests(unittest.TestCase):
    def test_extracts_steps_failures_and_source_references(self):
        result = parse_spool(SPOOL)
        self.assertEqual(result["max_return_code"], 12)
        self.assertEqual(result["failed_steps"][0]["step"], "COMPILE")
        self.assertEqual(result["abends"][0]["code"], "S0C7")
        self.assertEqual(result["file_statuses"][0]["code"], "35")
        self.assertEqual(result["compiler_diagnostics"][0]["line"], 7)
        self.assertFalse(result["ok"])
    def test_clean_spool_is_ok(self):
        result = parse_spool("STEP=RUN RC=0000\n")
        self.assertTrue(result["ok"])
        self.assertEqual(result["max_return_code"], 0)
    def test_spool_size_is_bounded(self):
        with self.assertRaises(ValueError):
            parse_spool("X" * (MAX_SPOOL_BYTES + 1))
class KnowledgeTests(unittest.TestCase):
    def test_unknown_fallback_is_explicit(self):
        result = lookup(None, "abend", "S0C7")
        self.assertFalse(result["matched"])
        self.assertEqual(result["code"], "S0C7")
        self.assertTrue(result["checks"])
    def test_site_catalog_extends_builtin_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / ".peacobol" / "knowledge"
            target.mkdir(parents=True)
            (target / "abend.json").write_text(json.dumps({"S0C7": {"title": "Site entry", "summary": "Approved local guidance.", "checks": ["Follow the approved local runbook."]}}), encoding="utf-8")
            result = lookup(root, "abend", "S0C7")
            self.assertTrue(result["matched"])
            self.assertEqual(result["title"], "Site entry")
            self.assertIn("UNKNOWN", load_catalog(root, "abend"))
    def test_invalid_catalog_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / ".peacobol" / "knowledge"
            target.mkdir(parents=True)
            (target / "file-status.json").write_text(json.dumps({"BAD CODE": {"title": "x", "summary": "y", "checks": ["z"]}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                list_knowledge(root)
class SecurityRegressionTests(unittest.TestCase):
    def test_dangerous_compiler_flag_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "peacobol.json").write_text(json.dumps({"profiles": {"development": {"compiler": {"flags": ["-j"]}}}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_profile(root, "development")
    def test_symlinked_audit_log_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.txt"; target.write_text("UNCHANGED\n", encoding="utf-8")
            log = root / "audit.jsonl"
            try:
                log.symlink_to(target)
            except OSError:
                self.skipTest("Symlinks are unavailable")
            with self.assertRaises(ValueError):
                append_event(log, "scan", "project", "success")
            self.assertEqual(target.read_text(encoding="utf-8"), "UNCHANGED\n")
            self.assertFalse(verify_log(log)["ok"])
class InvestigationTests(unittest.TestCase):
    def _project(self, directory):
        root = Path(directory)
        source = root / "src" / "PAYMENT.cbl"
        source.parent.mkdir(parents=True)
        source.write_text("\n".join(f"LINE {i}" for i in range(1, 15)) + "\n", encoding="utf-8")
        return root, source
    def test_diagnosis_correlates_bounded_source_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self._project(directory)
            result = diagnose(root, SPOOL, context_lines=2)
            context = result["source_context"][0]
            self.assertTrue(context["available"])
            self.assertEqual(context["context_start"], 5)
            self.assertEqual(context["context_end"], 9)
            self.assertEqual(len(context["sha256"]), 64)
            self.assertGreaterEqual(len(result["checklist"]), 6)
    def test_source_traversal_is_not_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self._project(directory)
            result = diagnose(root, "../outside.cbl:1: error: bad\n")
            self.assertFalse(result["source_context"][0]["available"])
    def test_symlinked_source_alias_is_not_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self._project(directory)
            secret = root / "secret.txt"; secret.write_text("SECRET", encoding="utf-8")
            alias = root / "leak.cbl"
            try:
                alias.symlink_to(secret)
            except OSError:
                self.skipTest("Symlinks are unavailable")
            result = diagnose(root, "leak.cbl:1: error: bad\n")
            self.assertFalse(result["source_context"][0]["available"])
    def test_context_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self._project(directory)
            with self.assertRaises(ValueError):
                diagnose(root, SPOOL, context_lines=9)
    def test_failure_bundle_is_repeatable_and_hashed(self):
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self._project(directory)
            spool = root / "failure.log"
            spool.write_text(SPOOL, encoding="utf-8")
            first = failure_bundle(root, spool, "bundle.json", 2)
            second = failure_bundle(root, spool, "bundle.json", 2)
            self.assertEqual(first, second)
            self.assertEqual(len(first["spool_sha256"]), 64)
            self.assertEqual(len(first["bundle_hash"]), 64)
    def test_symlink_spool_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self._project(directory)
            target = root / "real.log"; target.write_text(SPOOL, encoding="utf-8")
            link = root / "link.log"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("Symlinks are unavailable")
            with self.assertRaises(FileNotFoundError):
                failure_bundle(root, link)
if __name__ == "__main__":
    unittest.main()
