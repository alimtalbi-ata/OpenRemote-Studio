import tempfile, unittest, json
from pathlib import Path
from unittest.mock import patch
import qa_evidence_report as m

def sample(state="passed"):
 return {"schema":"openremote.windows-qa-campaign.v1","overall":"passed" if state=="passed" else "incomplete", "reports":{name:{"status":state} for name in m.CHECK_NAMES}}

class EvidenceTests(unittest.TestCase):
 def test_valid_report(self):
  out=m.render(sample());self.assertIn("<table>",out);self.assertIn("Abdelhalim Talbi",out)
 def test_all_six(self):self.assertEqual(m.render(sample()).count("<tr><th scope="),6)
 def test_no_raw_sensitive_data(self):
  obj=sample();obj["reports"]["main"]["reason"]="password=secret /home/user/private"
  out=m.render(obj);self.assertNotIn("secret",out);self.assertNotIn("/home/user",out)
 def test_bad_schema(self):
  obj=sample();obj["schema"]="wrong"
  with self.assertRaises(ValueError):m.render(obj)
 def test_missing_check(self):
  obj=sample();del obj["reports"]["dialogs"]
  with self.assertRaises(ValueError):m.render(obj)
 def test_invalid_status(self):
  obj=sample();obj["reports"]["main"]["status"]="<script>"
  with self.assertRaises(ValueError):m.render(obj)
 def test_invalid_overall(self):
  obj=sample();obj["overall"]="PASS!!"
  with self.assertRaises(ValueError):m.render(obj)
 def test_blocked_not_passed(self):
  out=m.render(sample("blocked"));self.assertIn("incomplete",out)
 def test_cli_no_overwrite(self):
  with tempfile.TemporaryDirectory() as td:
   inp=Path(td)/"in.json";out=Path(td)/"out.html"
   inp.write_text(json.dumps(sample()),encoding="utf8")
   self.assertEqual(m.main(["--input",str(inp),"--output",str(out)]),0)
   with self.assertRaises(FileExistsError):m.main(["--input",str(inp),"--output",str(out)])
 def test_same_path_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/"a.json";p.write_text(json.dumps(sample()))
   with self.assertRaises(SystemExit):m.main(["--input",str(p),"--output",str(p)])
