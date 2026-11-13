import http.client
import json
import random
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from peacobol.copybook import parse_copybook
from peacobol.core import evidence
from peacobol.coverage import import_coverage
from peacobol.server import handler_for
from peacobol.testworkbench import cobol_check_stub, compare_golden, generate_cases
class TestCaseGenerationTests(unittest.TestCase):
    def test_generates_four_hashed_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            copybook = Path(directory) / "A.cpy"
            copybook.write_text("01 REC.\n 05 CODE PIC X(3).\n 05 AMOUNT PIC S9(3)V99 COMP-3.\n", encoding="utf-8")
            result = generate_cases(copybook)
            self.assertEqual(result["record_length"], 6)
            self.assertEqual([item["id"] for item in result["cases"]], ["typical", "minimum", "maximum", "invalid"])
            self.assertEqual(len(result["cases_hash"]), 64)
            self.assertTrue(all(len(bytes.fromhex(item["record_hex"])) == 6 for item in result["cases"]))
    def test_generates_cobol_check_starter(self):
        with tempfile.TemporaryDirectory() as directory:
            copybook = Path(directory) / "A.cpy"; copybook.write_text("01 REC.\n 05 CODE PIC X.\n", encoding="utf-8")
            text = cobol_check_stub("PAYMENT", generate_cases(copybook))
            self.assertIn("PROGRAM-ID. PAYMENT-TEST", text)
            self.assertIn("CALL 'PAYMENT' USING TEST-RECORD", text)
            self.assertIn("COBOL Check EXPECT/assertion", text)
            self.assertIn("CASE MAXIMUM", text)
    def test_rejects_invalid_program_name(self):
        with self.assertRaises(ValueError):
            cobol_check_stub("BAD NAME", {"cases": [], "record_length": 1})
    def test_signed_minimum_is_negative(self):
        with tempfile.TemporaryDirectory() as directory:
            copybook=Path(directory)/"S.cpy"; copybook.write_text("01 REC.\n 05 DISPLAY-N PIC S9(3).\n 05 PACKED-N PIC S9(3) COMP-3.\n",encoding="utf-8")
            result=generate_cases(copybook)
            minimum=next(item for item in result["cases"] if item["id"]=="minimum")
            self.assertTrue(minimum["values"]["REC"]["DISPLAY-N"].startswith("-"))
            self.assertTrue(minimum["values"]["REC"]["PACKED-N"].startswith("-"))
    def test_scaled_binary_uses_implied_decimal(self):
        with tempfile.TemporaryDirectory() as directory:
            copybook=Path(directory)/"B.cpy"; copybook.write_text("01 REC.\n 05 VALUE PIC S9(2)V9 COMP.\n",encoding="utf-8")
            result=generate_cases(copybook)
            maximum=next(item for item in result["cases"] if item["id"]=="maximum")
            minimum=next(item for item in result["cases"] if item["id"]=="minimum")
            self.assertEqual(bytes.fromhex(maximum["record_hex"]), (999).to_bytes(2,"big",signed=True))
            self.assertEqual(bytes.fromhex(minimum["record_hex"]), (-999).to_bytes(2,"big",signed=True))
class GoldenTests(unittest.TestCase):
    def test_matches_and_finds_first_difference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); a=root/"a.dat"; b=root/"b.dat"
            a.write_bytes(b"ABC"); b.write_bytes(b"AXC")
            result=compare_golden(a,b)
            self.assertFalse(result["ok"]); self.assertEqual(result["first_difference"],1)
            b.write_bytes(b"ABC"); self.assertTrue(compare_golden(a,b)["ok"])
    def test_symlinked_golden_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); actual=root/"actual"; expected=root/"expected"; actual.write_bytes(b"A"); expected.write_bytes(b"A")
            link=root/"link"
            try: link.symlink_to(actual)
            except OSError: return
            with self.assertRaises(FileNotFoundError): compare_golden(link,expected)
class CoverageTests(unittest.TestCase):
    def test_imports_and_links_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"coverage.json"
            path.write_text(json.dumps({"lines":[{"file":"A.cbl","line":1,"hits":2},{"file":"A.cbl","line":2,"hits":0}]}),encoding="utf-8")
            result=import_coverage(path)
            self.assertEqual(result["summary"]["percent"],50.0)
            self.assertFalse(result["evidence_verified"])
            self.assertEqual(len(result["coverage_hash"]),64)
    def test_rejects_invalid_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"coverage.json"; path.write_text('{"lines":[{"file":"A","line":0,"hits":-1}]}',encoding="utf-8")
            with self.assertRaises(ValueError): import_coverage(path)
    def test_rejects_empty_duplicate_and_fake_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"coverage.json"
            path.write_text('{"lines":[]}',encoding="utf-8")
            with self.assertRaises(ValueError): import_coverage(path)
            path.write_text('{"lines":[{"file":"A","line":1,"hits":1},{"file":"A","line":1,"hits":0}]}',encoding="utf-8")
            with self.assertRaises(ValueError): import_coverage(path)
            path.write_text('{"lines":[{"file":"A","line":1,"hits":1}]}',encoding="utf-8")
    def test_verified_evidence_defines_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/"project"; root.mkdir(); source=root/"A.cbl"; source.write_text("       PROGRAM-ID. A.\n       PROCEDURE DIVISION.\n           GOBACK.\n",encoding="utf-8")
            manifest=evidence(root); manifest_path=Path(directory)/"evidence.json"; manifest_path.write_text(json.dumps(manifest),encoding="utf-8")
            coverage=Path(directory)/"coverage.json"; coverage.write_text(json.dumps({"lines":[{"file":"A.cbl","line":1,"hits":1}]}),encoding="utf-8")
            result=import_coverage(coverage,manifest_path,root)
            self.assertTrue(result["evidence_verified"])
            self.assertEqual(result["summary"]["lines"],3)
            self.assertEqual(result["summary"]["covered"],1)
            self.assertEqual(result["evidence_hash"],manifest["manifest_hash"])
    def test_tampered_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/"project"; root.mkdir(); (root/"A.cbl").write_text("GOBACK.\n",encoding="utf-8")
            manifest=evidence(root); manifest["project"]="tampered"; manifest_path=Path(directory)/"evidence.json"; manifest_path.write_text(json.dumps(manifest),encoding="utf-8")
            coverage=Path(directory)/"coverage.json"; coverage.write_text('{"lines":[{"file":"A.cbl","line":1,"hits":1}]}',encoding="utf-8")
            with self.assertRaises(ValueError): import_coverage(coverage,manifest_path,root)
    def test_evidence_path_aliases_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/"project"; root.mkdir(); source=root/"A.cbl"; source.write_text("GOBACK.\n",encoding="utf-8")
            manifest=evidence(root); manifest["source_hashes"]["./A.cbl"]=manifest["source_hashes"]["A.cbl"]
            unsigned=dict(manifest); unsigned.pop("manifest_hash"); import hashlib
            manifest["manifest_hash"]=hashlib.sha256(json.dumps(unsigned,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
            manifest_path=Path(directory)/"evidence.json"; manifest_path.write_text(json.dumps(manifest),encoding="utf-8")
            coverage=Path(directory)/"coverage.json"; coverage.write_text('{"lines":[{"file":"A.cbl","line":1,"hits":1}]}',encoding="utf-8")
            with self.assertRaises(ValueError): import_coverage(coverage,manifest_path,root)
class ParserRobustnessTests(unittest.TestCase):
    def test_period_terminated_record_parses_all_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"standard.cpy"
            path.write_text("01 REC\n 05 CODE PIC X(3)\n 05 AMOUNT PIC 9(4).\n",encoding="utf-8")
            fields=parse_copybook(path)
            self.assertEqual([item.name for item in fields[0].children],["CODE","AMOUNT"])
    def test_continuation_clause_stays_with_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"continued.cpy"
            path.write_text("01 REC.\n 05 AMOUNT PIC S9(7)V99\n    COMP-3.\n",encoding="utf-8")
            field=parse_copybook(path)[0].children[0]
            self.assertEqual(field.usage,"COMP-3")
    def test_fixed_format_continuation_indicator_is_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"fixed.cpy"
            path.write_text("000100 01 REC.\n000200 05 AMOUNT PIC S9(7)V99\n000300-    COMP-3.\n",encoding="utf-8")
            field=parse_copybook(path)[0].children[0]
            self.assertEqual(field.usage,"COMP-3")
            self.assertEqual(field.length,5)
    def test_fixed_format_direct_token_continuation_has_no_space(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"token.cpy"
            path.write_text("000100 01 REC.\n000200 05 CODE PIC X(1\n000300-0).\n",encoding="utf-8")
            field=parse_copybook(path)[0].children[0]
            self.assertEqual(field.picture,"X(10)")
            self.assertEqual(field.length,10)
    def test_random_malformed_copybooks_do_not_hang(self):
        rng=random.Random(42)
        alphabet=" ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789().-"
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"fuzz.cpy"
            for _ in range(100):
                lines=[''.join(rng.choice(alphabet) for _ in range(rng.randint(0,120))) for _ in range(rng.randint(1,20))]
                path.write_text('\n'.join(lines),encoding="utf-8")
                try: parse_copybook(path)
                except ValueError: pass
class GuiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        (self.root/"project"/"src").mkdir(parents=True); (self.root/"project"/"copybooks").mkdir()
        (self.root/"project"/"src"/"A.cbl").write_text("       PROGRAM-ID. A.\n       PROCEDURE DIVISION.\n           GOBACK.\n",encoding="utf-8")
        (self.root/"project"/"copybooks"/"A.cpy").write_text("01 REC.\n 05 CODE PIC X(3).\n",encoding="utf-8")
        (self.root/"schema.sql").write_text("CREATE TABLE T (\n CODE CHAR(3)\n);\n",encoding="utf-8")
        self.token="test-session-token"
        self.server=ThreadingHTTPServer(("127.0.0.1",0),handler_for(self.root.resolve(),self.token))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start(); self.cookie=None
        status,headers,_=self.get("/?token=test-session-token",use_cookie=False)
        self.assertEqual(status,303); self.cookie=headers["Set-Cookie"].split(";",1)[0]
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2); self.temp.cleanup()
    def get(self,path,host=None,use_cookie=True):
        conn=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=3); headers={"Host":host} if host else {}
        if use_cookie and self.cookie: headers["Cookie"]=self.cookie
        conn.request("GET",path,headers=headers); response=conn.getresponse(); data=response.read().decode(); response_headers=dict(response.getheaders()); conn.close(); return response.status,response_headers,data
    def test_home_and_all_navigation_are_rendered(self):
        status,headers,body=self.get("/")
        self.assertEqual(status,200); self.assertIn("PeaCOBOL 1.3.0",body); self.assertIn("Test cases",body); self.assertIn("Enterprise resources",body); self.assertIn("SBOM",body); self.assertNotIn("test-session-token",body); self.assertIn("default-src 'none'",headers["Content-Security-Policy"]); self.assertEqual(headers["Cache-Control"],"no-store")
    def test_scan_and_test_case_workbenches(self):
        status,_,body=self.get("/?view=scan&project=project")
        self.assertEqual(status,200); self.assertIn("Programs",body)
        status,_,body=self.get("/?view=tests&copybook=project%2Fcopybooks%2FA.cpy&program=A")
        self.assertEqual(status,200); self.assertIn("COBOL Check-compatible starter",body); self.assertIn("A-TEST",body)
    def test_enterprise_workbenches(self):
        status,_,body=self.get("/?view=resources&project=project")
        self.assertEqual(status,200); self.assertIn("Resource inventory",body)
        status,_,body=self.get("/?view=db2&copybook=project%2Fcopybooks%2FA.cpy&ddl=schema.sql")
        self.assertEqual(status,200); self.assertIn("Compatibility details",body)
        status,_,body=self.get("/?view=sbom&project=project")
        self.assertEqual(status,200); self.assertIn("Software inventory",body)

    def test_traversal_and_symlinks_are_rejected(self):
        _,_,body=self.get("/?view=scan&project=..")
        self.assertIn("Unable to complete request",body)
        outside=self.root/"outside"; outside.mkdir(); link=self.root/"link"
        try: link.symlink_to(outside,target_is_directory=True)
        except OSError: return
        _,_,body=self.get("/?view=scan&project=link")
        self.assertIn("Symlink paths are not allowed",body)
    def test_unknown_route_is_404(self):
        status,_,_=self.get("/secret?token=test-session-token"); self.assertEqual(status,404)
    def test_missing_token_and_untrusted_host_are_forbidden(self):
        status,_,_=self.get("/",use_cookie=False); self.assertEqual(status,403)
        status,_,_=self.get("/",host="attacker.example",use_cookie=False); self.assertEqual(status,403)
        status,_,_=self.get("/?token=test-session-token",use_cookie=False); self.assertEqual(status,403)
if __name__ == "__main__": unittest.main()
