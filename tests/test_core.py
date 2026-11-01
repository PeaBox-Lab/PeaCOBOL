import tempfile, unittest
from pathlib import Path
from peacobol.core import storage_length, parse_copybook, scan_project, create_project
class CoreTests(unittest.TestCase):
 def test_storage(self):
  self.assertEqual(storage_length('S9(7)V99','COMP-3'),5)
  self.assertEqual(storage_length('X(12)','DISPLAY'),12)
 def test_copybook(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'A.cpy'; p.write_text(' 05 AMOUNT PIC S9(7)V99 COMP-3.\n 05 CODE PIC X(3).')
   f=parse_copybook(p); self.assertEqual([x.length for x in f],[5,3]); self.assertEqual(f[1].offset,5)
 def test_scan(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'A.cbl'; p.write_text(" CALL 'B'\n DIVIDE A BY B\n GO TO END-X\n")
   r=scan_project(Path(d)); self.assertEqual(r['calls'][0]['to'],'B'); self.assertTrue(any(x['rule']=='PC201' for x in r['findings']))
 def test_init(self):
  with tempfile.TemporaryDirectory() as d:
   create_project(Path(d)/'p','p'); self.assertTrue((Path(d)/'p/peacobol.json').exists())
if __name__=='__main__': unittest.main()
