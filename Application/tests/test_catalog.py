import unittest
from tool_catalog import TOOLS,search_tools
class CatalogTests(unittest.TestCase):
 def test_unique_actions(self):self.assertEqual(len({t[2] for t in TOOLS}),len(TOOLS))
 def test_search(self):self.assertTrue(any(t[2]=='sftp' for t in search_tools('fichiers')))
 def test_all(self):self.assertEqual(len(search_tools('')),len(TOOLS))
