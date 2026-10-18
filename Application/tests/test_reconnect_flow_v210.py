"""V22.6 regression checks for safe reconnect ordering."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ReconnectFlowV210(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(ROOT/'qt_app.py').read_text()
    def test_overview_resolves_destination_before_consuming(self):
        method=self.source.split('    def reconnect_overview_session(self):',1)[1].split('    def _show_route_warning(self):',1)[0]
        self.assertLess(method.index('if destination is None:'),method.index('reconnect_candidate(identity,pid)'))
    def test_overview_rechecks_after_navigation(self):
        method=self.source.split('    def reconnect_overview_session(self):',1)[1].split('    def _show_route_warning(self):',1)[0]
        self.assertLess(method.index('reconnect_choice_still_valid('),method.index('reconnect_candidate(identity,pid)'))
    def test_connection_level_revalidates_store(self):
        method=self.source.split('    def reconnect_selected(self):',1)[1].split('    def connect(self):',1)[0]
        self.assertLess(method.index("any(item.get('id') == c['id']"),method.index("reconnect_candidate(c['id'],pid)"))
    def test_inno_setup_version_matches_release(self):
        self.assertIn('#include "version.generated.iss"',(ROOT/'windows/OpenRemoteStudio.iss').read_text())
if __name__=='__main__':unittest.main()
