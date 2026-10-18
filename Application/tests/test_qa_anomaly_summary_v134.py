import unittest
from qa_anomaly_summary import summarize,CHECKS

def report(status="passed"):
 return {"schema":"openremote.windows-qa-campaign.v1","reports":{k:{"status":status} for k in CHECKS}}
class AnomalyTests(unittest.TestCase):
 def test_pass(self):self.assertEqual(summarize(report())["overall"],"passed")
 def test_blocked(self):self.assertEqual(summarize(report("blocked"))["overall"],"incomplete")
 def test_failed(self):self.assertEqual(summarize(report("failed"))["overall"],"failed")
 def test_missing(self):
  r=report();del r["reports"]["main"]
  with self.assertRaises(ValueError):summarize(r)
 def test_bad_status(self):
  r=report();r["reports"]["main"]["status"]="success"
  with self.assertRaises(ValueError):summarize(r)
 def test_redaction(self):
  r=report("failed");r["reports"]["main"]["stderr"]="SECRET PASSWORD"
  self.assertNotIn("SECRET PASSWORD",str(summarize(r)))
 def test_network_not_claimed(self):self.assertFalse(summarize(report())["live_network_qualified"])
if __name__=="__main__":unittest.main()
