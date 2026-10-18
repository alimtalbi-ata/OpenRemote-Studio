import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class SessionKeyboardTests(unittest.TestCase):
 def setUp(self):self.src=(ROOT/'qt_app.py').read_text(encoding='utf-8')
 def test_shortcut_copy(self):self.assertIn("QKeySequence('Ctrl+C')",self.src)
 def test_shortcut_refresh(self):self.assertIn("QKeySequence('F5')",self.src)
 def test_accessible_name(self):self.assertIn("setAccessibleName('Liste des sessions externes')",self.src)
 def test_copy_resolves_unique_identity(self):
  section=self.src.split('    def copy_selected_session_details(self,*_):',1)[1].split('    def inspect_selected_session',1)[0]
  self.assertIn('selected_session(self.external_sessions.snapshot(),identity,pid)',section)
  self.assertIn('if row is None:',section)
 def test_copy_does_not_reconnect(self):
  section=self.src.split('    def copy_selected_session_details(self,*_):',1)[1].split('    def inspect_selected_session',1)[0]
  self.assertNotIn('reconnect_candidate(',section)
if __name__=='__main__':unittest.main()
