import ast,unittest
from pathlib import Path
class CancelTests(unittest.TestCase):
 def test_cancel_event_defined(self):
  source=(Path(__file__).resolve().parents[1]/'qt_workers.py').read_text()
  self.assertIn('self.cancel_event=Event()',source)
  self.assertIn("raise InterruptedError('Opération annulée')",source)
 def test_cancel_ui_is_wired(self):
  source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
  self.assertIn("cancel_button.clicked.connect",source)
  self.assertIn("active_jobs.append(job)",source)
 def test_syntax(self):
  for filename in ('qt_app.py','qt_workers.py'):
   ast.parse((Path(__file__).resolve().parents[1]/filename).read_text())
