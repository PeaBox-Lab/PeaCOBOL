import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from peacobol.copybook import parse_copybook
from peacobol.core import build, create_project, scan_project
from peacobol.diagnostics import diagnostic_summary, normalize_diagnostics
from peacobol.jcl import generate_jcl
from peacobol.policy import evaluate_policy
from peacobol.profiles import list_profiles, load_profile, resolve_profile_name
from peacobol.records import decode_record
class ProfileTests(unittest.TestCase):
    def test_all_versioned_profiles_load(self):
        result = list_profiles()
        self.assertEqual([item["name"] for item in result["profiles"]], ["development", "release", "banking", "aerospace"])
        self.assertEqual(load_profile(None, "banking")["data"]["encoding"], "cp037")
    def test_project_override_is_merged_and_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "peacobol.json").write_text(json.dumps({"profiles": {"release": {"data": {"binary_byteorder": "little"}}}}), encoding="utf-8")
            profile = load_profile(root, "release")
            self.assertEqual(profile["data"]["binary_byteorder"], "little")
            self.assertEqual(profile["data"]["encoding"], "ascii")
    def test_invalid_override_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "peacobol.json").write_text(json.dumps({"profiles": {"release": {"data": {"encoding": "unknown"}}}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_profile(root, "release")
    def test_project_default_profile_is_resolved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "peacobol.json").write_text(json.dumps({"default_profile": "banking"}), encoding="utf-8")
            self.assertEqual(resolve_profile_name(root, None, "development"), "banking")
            self.assertEqual(resolve_profile_name(root, "release", "development"), "release")
    def test_jcl_profile_injection_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "peacobol.json").write_text(json.dumps({"profiles": {"release": {"jcl": {"compiler": "IGYCRCTL\n//BAD"}}}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_profile(root, "release")
class DiagnosticTests(unittest.TestCase):
    def test_gnucobol_and_ibm_diagnostics_are_normalized(self):
        text = "A.cbl:12:7: warning: value is unused\ncobc: warning: driver option ignored\nIGYPS2121-S Invalid statement Line: 44\n"
        result = normalize_diagnostics(text)
        self.assertEqual(result[0]["severity"], "warning")
        self.assertEqual(result[0]["column"], 7)
        self.assertEqual(result[1]["tool"], "cobc")
        self.assertEqual(result[2]["tool"], "ibm-enterprise-cobol")
        self.assertEqual(result[2]["severity"], "error")
        self.assertEqual(diagnostic_summary(result), {"error": 1, "warning": 2, "note": 0})
class JclTests(unittest.TestCase):
    def test_compile_link_run_jcl_uses_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            result = generate_jcl(Path(directory), "PAYMENT", "banking", "BANK.COBOL.SOURCE", "BANK.COBOL.LOAD", "BANK.COBOL.COPY")
            self.assertIn("//COMPILE", result["jcl"])
            self.assertIn("NUMCHECK", result["jcl"])
            self.assertIn("BANK.COBOL.SOURCE(PAYMENT)", result["jcl"])
            self.assertIn("IGY.V6R4M0.SIGYCOMP", result["jcl"])
            self.assertIn("CEE.RUNLIB.LOAD", result["jcl"])
            self.assertIn("//RUN", result["jcl"])
    def test_invalid_dataset_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                generate_jcl(Path(directory), "PAYMENT", source_dataset="INVALID DATASET")
class RepresentationTests(unittest.TestCase):
    def test_profile_driven_little_endian_binary_decode(self):
        with tempfile.TemporaryDirectory() as directory:
            copybook = Path(directory) / "B.cpy"
            copybook.write_text("01 REC.\n 05 VALUE PIC S9(4) COMP.\n", encoding="utf-8")
            result = decode_record(parse_copybook(copybook), (258).to_bytes(2, "little", signed=True), binary_byteorder="little")
            self.assertEqual(result["REC"]["VALUE"], 258)
    def test_invalid_byteorder_is_rejected(self):
        with self.assertRaises(ValueError):
            decode_record([], b"", binary_byteorder="middle")
class PolicyTests(unittest.TestCase):
    def test_release_gate_requires_clean_high_findings_and_evidence(self):
        profile = load_profile(None, "release")
        scan = {"summary": {"findings": {"critical": 0, "high": 1, "medium": 0, "low": 0}}}
        result = evaluate_policy(profile, scan, {"ok": True, "diagnostic_summary": {"warning": 0}}, None)
        self.assertFalse(result["ok"])
        self.assertIn("findings-high", result["failed_checks"])
        self.assertIn("evidence-required", result["failed_checks"])
    def test_development_gate_allows_high_findings(self):
        profile = load_profile(None, "development")
        scan = {"summary": {"findings": {"critical": 0, "high": 3, "medium": 2, "low": 1}}}
        self.assertTrue(evaluate_policy(profile, scan)["ok"])
class BuildManifestTests(unittest.TestCase):
    @patch("peacobol.core.subprocess.run")
    @patch("peacobol.core.shutil.which", return_value="/usr/bin/cobc")
    def test_build_normalizes_diagnostics_and_hashes_manifest(self, _, run):
        def compile_ok(args, **kwargs):
            target = Path(args[args.index("-o") + 1])
            target.write_bytes(b"executable")
            return Mock(returncode=0, stdout="", stderr="A.cbl:2: warning: check this")
        run.side_effect = compile_ok
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A.cbl").write_text("       IDENTIFICATION DIVISION.\n       PROGRAM-ID. A.\n", encoding="utf-8")
            result = build(root, profile_name="development")
            self.assertTrue(result["ok"])
            self.assertEqual(result["diagnostic_summary"]["warning"], 1)
            self.assertIn("artifact_sha256", result["results"][0])
            self.assertEqual(len(result["manifest"]["manifest_hash"]), 64)
            args = run.call_args.args[0]
            self.assertIn("-Wall", args)
            self.assertFalse(run.call_args.kwargs["shell"])
    @patch("peacobol.core.subprocess.run", return_value=Mock(returncode=0, stdout="", stderr=""))
    @patch("peacobol.core.shutil.which", return_value="/usr/bin/cobc")
    def test_build_fails_when_compiler_creates_no_artifact(self, _, run):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A.cbl").write_text("       IDENTIFICATION DIVISION.\n       PROGRAM-ID. A.\n", encoding="utf-8")
            stale = root / "build" / "A"
            stale.parent.mkdir()
            stale.write_bytes(b"stale")
            result = build(root)
            self.assertFalse(result["ok"])
            self.assertFalse(stale.exists())
            self.assertEqual(result["diagnostic_summary"]["error"], 1)
    @patch("peacobol.core.subprocess.run")
    @patch("peacobol.core.shutil.which", return_value="/usr/bin/cobc")
    def test_build_disambiguates_cbl_and_cob_targets(self, _, run):
        def compile_ok(args, **kwargs):
            Path(args[args.index("-o") + 1]).write_bytes(b"executable")
            return Mock(returncode=0, stdout="", stderr="")
        run.side_effect = compile_ok
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A.cbl").write_text("       PROGRAM-ID. A.\n", encoding="utf-8")
            (root / "A.cob").write_text("       PROGRAM-ID. B.\n", encoding="utf-8")
            result = build(root)
            targets = {item["target"] for item in result["results"]}
            self.assertTrue(result["ok"])
            self.assertEqual(targets, {"build/A-cbl", "build/A-cob"})
class ProjectTests(unittest.TestCase):
    def test_new_project_exposes_all_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, "project")
            config = json.loads((root / "peacobol.json").read_text(encoding="utf-8"))
            self.assertEqual(config["version"], "1.2.0")
            self.assertEqual(set(config["profiles"]), {"development", "release", "banking", "aerospace"})
            self.assertEqual(scan_project(root)["schema"], "peacobol-scan-3")
if __name__ == "__main__":
    unittest.main()
