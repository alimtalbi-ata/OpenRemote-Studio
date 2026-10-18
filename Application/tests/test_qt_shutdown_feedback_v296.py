from pathlib import Path
import unittest

class ShutdownFeedbackContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
    def test_tab_shutdown_feedback_before_wait(self):
        body=self.code.split('    def close_tab(self,index):',1)[1].split('    def show_integrations(',1)[0]
        self.assertLess(body.index("showMessage('Arrêt SSH en cours (interface disponible)…'"),body.index('QTimer.singleShot(100,finish_when_stopped)'))
    def test_window_shutdown_feedback_before_wait(self):
        body=self.code.split('    def closeEvent(self,event):',1)[1].split('    def lock_vault(',1)[0]
        self.assertLess(body.index("showMessage('Fermeture SSH en cours…'"),body.index('QTimer.singleShot(100,finish_window_shutdown)'))
    def test_refused_close_keeps_user_informed(self):
        self.assertIn('Arrêt SSH non confirmé : onglet conservé',self.code)
        self.assertIn('Fermeture reportée : session SSH toujours active',self.code)
