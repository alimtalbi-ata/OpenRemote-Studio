import unittest
from pathlib import Path
from connection_filter_state import filter_status

class FilterStateTests(unittest.TestCase):
    def test_empty(self): self.assertIn('Aucune connexion',filter_status(0,0)[0])
    def test_no_match(self): self.assertEqual(filter_status(3,0,'missing')[1],True)
    def test_favorites(self): self.assertTrue(filter_status(3,0,'',True)[1])
    def test_normal(self): self.assertEqual(filter_status(2,2),('2 connexions',False))
    def test_filtered_count(self): self.assertEqual(filter_status(5,1,'ssh')[0],'1 connexion sur 5')
    def test_bad_counts(self):
        with self.assertRaises(ValueError):filter_status(1,2)
    def test_ui_wiring(self):
        source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        self.assertIn('def reset_connection_filters(self):',source)
        self.assertIn('filter_status(len(self.store.items),visible,query',source)
