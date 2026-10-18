import pathlib, unittest
class GuidanceUITests(unittest.TestCase):
 def test_guidance_button_and_handler(self):
  src=(pathlib.Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
  self.assertIn("setObjectName('guidedSessionDiagnosis')",src)
  self.assertIn('def show_selected_session_guidance(self):',src)
  self.assertIn('selected_session(self.external_sessions.snapshot()',src)
  self.assertIn('format_guided_diagnostic(row)',src)
  self.assertIn('self.session_guided_button.setEnabled',src)
if __name__=='__main__':unittest.main()
