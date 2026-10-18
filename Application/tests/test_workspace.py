import tempfile, unittest
from pathlib import Path
from workspace import Workspace
class WorkspaceTests(unittest.TestCase):
    def test_favorites_and_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'workspace.json';w=Workspace(p)
            w.toggle_favorite('server-1');w.mark_recent('server-1')
            self.assertEqual(Workspace(p).data['favorites'],['server-1'])
            w.toggle_favorite('server-1');self.assertEqual(Workspace(p).data['favorites'],[])
    def test_recent_bounded_and_purge(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workspace(Path(d)/'w.json')
            for i in range(25):w.mark_recent(str(i))
            self.assertEqual(len(w.data['recent']),20)
            w.toggle_favorite('24');w.purge('24')
            self.assertNotIn('24',w.data['recent'])
            self.assertNotIn('24',w.data['favorites'])
