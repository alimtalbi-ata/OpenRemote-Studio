import unittest
from ssh_import_audit import validate_rows,filter_rows,summary,export_signed,verify_signed
ROW={'imported_at':100,'total':3,'inserted':2,'duplicates':1,'conflicts':1}
KEY=b'correct-audit-key-with-32-bytes!!'
class AuditTests(unittest.TestCase):
 def test_valid(self):self.assertEqual(validate_rows([ROW]),[ROW])
 def test_summary(self):self.assertEqual(summary([ROW])['duplicates'],1)
 def test_filter(self):self.assertEqual(filter_rows([ROW],since=101),[])
 def test_conflict(self):self.assertEqual(len(filter_rows([ROW],conflicts_only=True)),1)
 def test_roundtrip(self):self.assertEqual(verify_signed(export_signed([ROW],KEY),KEY),[ROW])
 def test_tamper(self):
  e=export_signed([ROW],KEY);e['payload']['rows'][0]['total']=4
  with self.assertRaises(ValueError):verify_signed(e,KEY)
 def test_wrong_key(self):
  with self.assertRaises(ValueError):verify_signed(export_signed([ROW],KEY),b'other-key-with-32-bytes-length!!!')
 def test_bad_counts(self):
  with self.assertRaises(ValueError):validate_rows([{**ROW,'duplicates':4}])
 def test_extra_identity(self):
  with self.assertRaises(ValueError):validate_rows([{**ROW,'host':'secret'}])
 def test_limit(self):
  with self.assertRaises(ValueError):filter_rows([ROW],limit=101)
