
import unittest
from profiles import PROFILES, visible_tools
from tool_catalog import TOOLS
class ProfileTests(unittest.TestCase):
    def test_all_shows_every_tool(self):
        self.assertEqual(visible_tools(TOOLS,"Tous"),list(TOOLS))
    def test_network_filters_out_workspace(self):
        self.assertTrue(all(t[0]!="Espace de travail" for t in visible_tools(TOOLS,"Réseau")))
    def test_query_combines_with_profile(self):
        self.assertEqual([t[2] for t in visible_tools(TOOLS,"Réseau","dns")],["nslookup"])
    def test_unknown_profile_fails_closed(self):
        with self.assertRaises(ValueError):visible_tools(TOOLS,"admin")
    def test_no_tools_removed_from_catalog(self):
        self.assertEqual(len(TOOLS),10)
