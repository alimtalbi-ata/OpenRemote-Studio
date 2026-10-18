import unittest
from unittest.mock import patch
import windows_qa_campaign as m
class CampaignTests(unittest.TestCase):
 def test_six_checks(self):self.assertEqual(len(m.CHECKS),6)
 def test_timeout_invalid(self):
  for value in (0,121,True,"10"):
   with self.assertRaises(ValueError):m.campaign(timeout=value)
 def test_missing_qt_blocked(self):
  with patch.object(m.importlib.util,"find_spec",return_value=None):
   report=m.campaign()
  self.assertEqual(report["overall"],"incomplete")
  self.assertEqual(report["counts"]["blocked"],6)
  self.assertFalse(report["live_network_tests_executed"])
 def test_all_pass(self):
  from unittest.mock import MagicMock
  def fake_run(argv,**kwargs):
   from pathlib import Path
   import json
   Path(argv[argv.index("--output")+1]).write_text(json.dumps({"status":"passed","schema":"test"}))
   return MagicMock(returncode=0)
  with patch.object(m.importlib.util,"find_spec",return_value=object()):
   report=m.campaign(runner=fake_run)
  self.assertEqual(report["overall"],"passed")
 def test_missing_report_fails(self):
  from unittest.mock import MagicMock
  with patch.object(m.importlib.util,"find_spec",return_value=object()):
   report=m.campaign(runner=lambda *a,**k:MagicMock(returncode=1))
  self.assertEqual(report["overall"],"failed")
 def test_bad_report_fails(self):
  from unittest.mock import MagicMock
  def fake(argv,**kwargs):
   from pathlib import Path
   Path(argv[argv.index("--output")+1]).write_text("not json")
   return MagicMock(returncode=0)
  with patch.object(m.importlib.util,"find_spec",return_value=object()):
   report=m.campaign(runner=fake)
  self.assertEqual(report["counts"]["failed"],6)
if __name__=="__main__":unittest.main()
