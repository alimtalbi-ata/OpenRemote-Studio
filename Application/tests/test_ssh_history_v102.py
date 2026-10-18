import tempfile,unittest,time
from pathlib import Path
from ssh_diagnostic_history import DiagnosticHistory

REPORT={'schema':'openremote.ssh-diagnostic.v1','status':'authenticated','steps':[{'step':'Bastion principal','state':'ok','duration_ms':120}]}
class HistoryV102(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=DiagnosticHistory(Path(self.tmp.name)/'history.sqlite3')
 def tearDown(self):self.tmp.cleanup()
 def test_empty_statistics(self):
  result=self.db.statistics();self.assertEqual(result['count'],0);self.assertEqual(result['series']['Bastion principal'],[])
 def test_series_and_aggregate(self):
  self.db.add(REPORT);result=self.db.statistics();self.assertEqual(result['count'],1);self.assertEqual(result['steps'][0]['average_ms'],120)
 def test_future_since(self):
  self.db.add(REPORT);self.assertEqual(self.db.statistics(since=int(time.time())+3600)['count'],0)
 def test_status_filter(self):
  self.db.add(REPORT);self.assertEqual(self.db.statistics(status='failed')['count'],0)
 def test_bad_status(self):
  with self.assertRaises(ValueError):self.db.statistics(status='not-a-status')
 def test_source_has_real_qt_painter(self):
  src=(Path(__file__).resolve().parents[1]/'ssh_history_dashboard.py').read_text();self.assertIn('class LatencyPlot(QWidget)',src);self.assertIn('painter.drawLine',src)
