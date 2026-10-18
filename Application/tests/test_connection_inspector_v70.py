import unittest
from connection_inspector import inspect_connection

class InspectorTests(unittest.TestCase):
    def setUp(self):self.c={'id':'id-1','name':'Prod','protocol':'SSH','host':'server.example','port':'22','group':'Infra','user':'secretuser','password':'do-not-show'}
    def test_no_selection(self):self.assertIn('Sélectionnez',inspect_connection(None))
    def test_no_secrets(self):
        result=inspect_connection(self.c)
        self.assertNotIn('secretuser',result)
        self.assertNotIn('do-not-show',result)
    def test_favorite(self):self.assertIn('Favori : Oui',inspect_connection(self.c,['id-1']))
    def test_active(self):self.assertIn('Client local actif : Oui',inspect_connection(self.c,active_ids=['id-1']))
    def test_remote_unverified(self):self.assertIn('non vérifié',inspect_connection(self.c))

if __name__=='__main__':unittest.main()
