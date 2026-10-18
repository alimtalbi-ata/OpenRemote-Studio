import unittest
from inventory import inventory, summary, export_csv, export_json
import json
class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.items=[{'name':'Host','protocol':'SSH','host':'example.org','port':'22','user':'admin','group':'Prod','tags':'linux','password':'DO_NOT_EXPORT'}, {'name':'=CMD','protocol':'RDP','host':'host2','group':'Prod'}]
    def test_counts(self):
        self.assertEqual(summary(self.items)['total'],2)
        self.assertEqual(summary(self.items)['protocols']['SSH'],1)
    def test_no_secrets(self):
        self.assertNotIn('DO_NOT_EXPORT',export_json(self.items))
        self.assertNotIn('DO_NOT_EXPORT',export_csv(self.items))
    def test_csv_injection(self):
        self.assertIn("'=CMD",export_csv(self.items))
    def test_json_schema(self):
        self.assertEqual(json.loads(export_json(self.items))['schema'],'openremote-inventory-v1')
if __name__=='__main__':unittest.main()
