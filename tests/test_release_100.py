"""Release-hardening tests for 1.1.1: rules integrity and signed releases."""

import copy
import os
import tempfile
import unittest
from pathlib import Path

from peacobol.core import scan_project
from peacobol.assurance import analyze_assurance
from peacobol.rulesintegrity import MANIFEST_SCHEMA, rules_manifest, verify_rules_manifest
from peacobol.supplychain import sign_release, verify_release


class RulesIntegrityTests(unittest.TestCase):
    def test_manifest_is_reproducible_and_hashed(self):
        first = rules_manifest()
        second = rules_manifest()
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], MANIFEST_SCHEMA)
        self.assertEqual(len(first["manifest_hash"]), 64)
        for module, entry in first["rule_sources"].items():
            self.assertEqual(len(entry["sha256"]), 64)
            self.assertIn(module, ("peacobol.core", "peacobol.assurance"))

    def test_verification_of_current_manifest_passes(self):
        manifest = rules_manifest()
        result = verify_rules_manifest(manifest)
        self.assertTrue(result["ok"])

    def test_tampered_manifest_is_rejected(self):
        manifest = rules_manifest()
        forged = copy.deepcopy(manifest)
        forged["manifest_hash"] = "0" * 64
        self.assertFalse(verify_rules_manifest(forged)["ok"])

    def test_missing_manifest_hash_is_rejected(self):
        self.assertFalse(verify_rules_manifest({"schema": MANIFEST_SCHEMA})["ok"])

    def test_reports_embed_current_rules_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A.cbl").write_text("       GOBACK.\n", encoding="utf-8")
            current = rules_manifest()["manifest_hash"]
            self.assertEqual(scan_project(root)["rules_manifest_hash"], current)
            self.assertEqual(analyze_assurance(root, "none")["rules_manifest_hash"], current)


class ReleaseSigningTests(unittest.TestCase):
    KEY = "release-key-that-is-definitely-32-bytes-long"

    def setUp(self):
        self.previous = os.environ.get("PEACOBOL_ATTESTATION_KEY")
        os.environ["PEACOBOL_ATTESTATION_KEY"] = self.KEY

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("PEACOBOL_ATTESTATION_KEY", None)
        else:
            os.environ["PEACOBOL_ATTESTATION_KEY"] = self.previous

    def test_sign_release_and_verify_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "scan.json"; report.write_text('{"ok": true}', encoding="utf-8")
            archive = root / "release.tar.gz"
            envelope = sign_release([report], archive, "PeaCOBOL-1.1.1")
            self.assertEqual(envelope["release"], "PeaCOBOL-1.1.1")
            self.assertEqual(envelope["signature_algorithm"], "HMAC-SHA256")
            self.assertTrue(archive.is_file())
            self.assertTrue(verify_release(envelope, archive)["ok"])

    def test_altered_archive_fails_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.json"; report.write_text("{}", encoding="utf-8")
            archive = root / "release.tar.gz"
            envelope = sign_release([report], archive, "REL")
            archive.write_bytes(archive.read_bytes() + b"tampered")
            result = verify_release(envelope, archive)
            self.assertFalse(result["ok"])

    def test_tampered_envelope_fails_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.json"; report.write_text("{}", encoding="utf-8")
            archive = root / "release.tar.gz"
            envelope = sign_release([report], archive, "REL")
            envelope["statement"]["predicate"]["releaseName"] = "Forged"
            self.assertFalse(verify_release(envelope, archive)["ok"])

    def test_signature_requires_strong_key(self):
        os.environ["PEACOBOL_ATTESTATION_KEY"] = "short"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.json"; report.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                sign_release([report], root / "release.tar.gz", "REL")

    def test_invalid_release_name_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.json"; report.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                sign_release([report], root / "release.tar.gz", "in valid")


if __name__ == "__main__":
    unittest.main()
