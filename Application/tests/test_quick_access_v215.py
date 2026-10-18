import unittest
from pathlib import Path
from dashboard import quick_access

ROOT=Path(__file__).resolve().parents[1]

class QuickAccessV215Tests(unittest.TestCase):
    def setUp(self):
        self.one=dict(id='a',name='Alpha',host='alpha',protocol='SSH')
    def test_ambiguous_id_is_not_launchable(self):
        rows=[self.one,dict(self.one,name='Impostor')]
        self.assertEqual(quick_access(rows,{'favorites':['a']}),[])
    def test_unique_id_still_available(self):
        self.assertEqual(quick_access([self.one],{'recent':['a']})[0]['id'],'a')
    def test_missing_id_is_skipped(self):
        self.assertEqual(quick_access([dict(name='Bad')],{'favorites':['a']}),[])
    def test_blank_id_is_skipped(self):
        self.assertEqual(quick_access([dict(self.one,id='')],{'favorites':['']}),[])
    def test_keyboard_activation(self):
        text=(ROOT/'qt_app.py').read_text(encoding='utf-8')
        self.assertIn('quick_access_list.itemActivated.connect',text)
    def test_empty_state_visible(self):
        text=(ROOT/'qt_app.py').read_text(encoding='utf-8')
        self.assertIn('Aucun favori ni connexion récente',text)
    def test_ambiguous_selection_blocked(self):
        text=(ROOT/'qt_app.py').read_text(encoding='utf-8')
        self.assertIn("sum(c['id']==identity for c in self.store.items)!=1",text)
