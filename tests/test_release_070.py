import json
import os
import tarfile
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from peacobol.cli import main as cli_main
from peacobol.enterprise import db2_compatibility, resource_inventory, submission_plan
from peacobol.supplychain import attest, immutable_export, retention_plan, sbom, verify_attestation


class Db2Tests(unittest.TestCase):
    def test_copybook_ddl_compatibility(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); copybook=root/"ACCOUNT.cpy"; ddl=root/"schema.sql"
            copybook.write_text("01 REC.\n 05 ACCOUNT-ID PIC X(12).\n 05 BALANCE PIC S9(9)V99 COMP-3.\n",encoding="utf-8")
            ddl.write_text("CREATE TABLE ACCOUNT (\n ACCOUNT_ID CHAR(12),\n BALANCE DECIMAL(11,2)\n);\n",encoding="utf-8")
            result=db2_compatibility(copybook,ddl)
            self.assertTrue(result["ok"])
            self.assertEqual(result["summary"],["unexpected"] if False else {"columns":2,"compatible":2,"incompatible":0})
            self.assertEqual(len(result["manifest_hash"]),64)

    def test_multiline_decimal_scale_mismatch_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); copybook=root/"A.cpy"; ddl=root/"A.sql"
            copybook.write_text("01 REC.\n 05 AMOUNT PIC 9(9)V9 COMP-3.\n",encoding="utf-8")
            ddl.write_text("CREATE TABLE T (\n AMOUNT DECIMAL\n (9, 2)\n);",encoding="utf-8")
            result=db2_compatibility(copybook,ddl)
            self.assertFalse(result["ok"]); self.assertIn("scale",result["results"][0]["reason"].lower())

    def test_incompatible_column_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); copybook=root/"A.cpy"; ddl=root/"A.sql"
            copybook.write_text("01 REC.\n 05 CODE PIC X(2).\n",encoding="utf-8")
            ddl.write_text("CREATE TABLE T (\n CODE CHAR(10)\n);",encoding="utf-8")
            result=db2_compatibility(copybook,ddl)
            self.assertFalse(result["ok"]); self.assertEqual(result["summary"]["incompatible"],1)


class ResourceTests(unittest.TestCase):
    def test_db2_cics_mq_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"A.cbl").write_text(" EXEC SQL\n SELECT X\n FROM APP.TABLE\n END-EXEC\n EXEC CICS\n READ FILE('ACCT')\n END-EXEC\n CALL 'MQPUT'\n USING HCONN\n",encoding="utf-8")
            result=resource_inventory(root)
            self.assertEqual(result["summary"],{"db2":1,"cics":1,"mq":1})
            self.assertEqual(result["cics"][0]["resources"][0]["name"],"ACCT")


class SubmissionPlanTests(unittest.TestCase):
    def test_validated_dry_run_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); jcl=root/"JOB.jcl"; jcl.write_text("//JOB JOB\n",encoding="utf-8")
            allow=root/"allow.json"; allow.write_text(json.dumps({"systems":{"DEV":{"enabled":True,"url":"https://zos.example.invalid","roles":["developer"]}}}),encoding="utf-8")
            result=submission_plan(root,jcl,"DEV",allow,"developer","vault://mainframe/dev")
            self.assertEqual(result["mode"],"dry-run-only"); self.assertTrue(result["tls_verify"]); self.assertIn("no network",result["notice"].lower())

    def test_secret_bearing_urls_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); jcl=root/"JOB.jcl"; jcl.write_text("//JOB JOB\n",encoding="utf-8")
            for url in ("https://user:password@host", "https://host/path?token=secret", "https://host/path#secret"):
                allow=root/"allow.json"; allow.write_text(json.dumps({"systems":{"DEV":{"enabled":True,"url":url,"roles":["developer"]}}}),encoding="utf-8")
                with self.assertRaises(ValueError): submission_plan(root,jcl,"DEV",allow,"developer","vault://mainframe/dev")

    def test_unlisted_system_and_inline_credential_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); jcl=root/"JOB.jcl"; jcl.write_text("//JOB JOB\n",encoding="utf-8")
            allow=root/"allow.json"; allow.write_text('{"systems":{}}',encoding="utf-8")
            with self.assertRaises(ValueError): submission_plan(root,jcl,"DEV",allow,"developer","password")


class SupplyChainTests(unittest.TestCase):
    def test_sbom_includes_hashed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/"pyproject.toml").write_text('[project]\nversion="0.7.0"\n',encoding="utf-8"); (root/"A.txt").write_text("x",encoding="utf-8")
            result=sbom(root)
            self.assertEqual(result["metadata"]["component"]["version"],"0.7.0")
            self.assertEqual(len(result["components"]),2); self.assertEqual(result["components"][0]["type"],"file"); self.assertEqual(len(result["bom_hash"]),64)

    def test_attestation_sign_and_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"artifact.zip"; path.write_bytes(b"artifact")
            previous=os.environ.get("PEACOBOL_ATTESTATION_KEY"); os.environ["PEACOBOL_ATTESTATION_KEY"]="test-key-that-is-at-least-32-bytes-long"
            try:
                envelope=attest(path); self.assertTrue(verify_attestation(envelope)["ok"])
                envelope["statement"]["subject"][0]["name"]="tampered"; self.assertFalse(verify_attestation(envelope)["ok"])
            finally:
                if previous is None: os.environ.pop("PEACOBOL_ATTESTATION_KEY",None)
                else: os.environ["PEACOBOL_ATTESTATION_KEY"]=previous

    def test_failed_attestation_verification_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"unsigned.json"; path.write_text(json.dumps({"signature":None,"signature_algorithm":None,"statement":{}}),encoding="utf-8")
            self.assertEqual(cli_main(["--no-audit","attest",str(path),"--verify"]),3)

    def test_immutable_export_and_retention_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); first=root/"a.json"; second=root/"b.json"; first.write_text("{}",encoding="utf-8"); second.write_text("[]",encoding="utf-8")
            output=root/"evidence.tar.gz"; result=immutable_export([first,second],output)
            self.assertTrue(output.is_file()); self.assertEqual(len(result["export_id"]),64)
            with tarfile.open(output,"r:gz") as archive:
                self.assertIn("manifest.json",archive.getnames()); self.assertTrue(all(member.mode==0o600 for member in archive.getmembers()))
            other=root/"evidence2.tar.gz"; second_result=immutable_export([first,second],other); self.assertEqual(result["sha256"],second_result["sha256"])
            plan=retention_plan(root,1,datetime(2030,1,1,tzinfo=timezone.utc)); self.assertEqual(plan["mode"],"dry-run-only"); self.assertGreaterEqual(len(plan["candidates"]),2)


class LauncherTests(unittest.TestCase):
    def test_launchers_are_present_and_safe(self):
        root=Path(__file__).resolve().parents[1]
        windows=(root/"start.bat").read_text(encoding="utf-8"); linux=(root/"start-linux.sh").read_text(encoding="utf-8"); wsl=(root/"start-linux.bat").read_text(encoding="utf-8")
        self.assertIn("peacobol.server",windows); self.assertIn("--open-browser",windows); self.assertNotIn("pip install",windows.lower())
        self.assertIn("peacobol.server",linux); self.assertIn("--open-browser",linux); self.assertTrue(os.access(root/"start-linux.sh",os.X_OK))
        self.assertIn("wsl.exe",wsl)


if __name__ == "__main__": unittest.main()
