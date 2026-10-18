
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core import Store, validate

def sample(name='host', id=''):
    return dict(id=id, name=name, host='server.example', protocol='SSH',
                user='admin', group='', port='22', tags='')

class HardeningTests(unittest.TestCase):
    def test_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'connections.json'
            p.write_text(json.dumps([sample('a','same'),sample('b','same')]))
            with self.assertRaisesRegex(ValueError,'dupliqués'): Store(p)
    def test_upsert_rolls_back_on_io_failure(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'connections.json')
            store.upsert(sample('a'))
            before=list(store.items)
            with patch.object(store,'save',side_effect=OSError('disk full')):
                with self.assertRaises(OSError): store.upsert(sample('b'))
            self.assertEqual(store.items,before)
    def test_remove_rolls_back_on_io_failure(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'connections.json')
            store.upsert(sample('a'))
            before=list(store.items)
            with patch.object(store,'save',side_effect=OSError('disk full')):
                with self.assertRaises(OSError): store.remove(before[0]['id'])
            self.assertEqual(store.items,before)
    def test_import_rolls_back_on_io_failure(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'connections.json')
            imp=Path(d)/'import.json'
            imp.write_text(json.dumps([sample('a')]))
            with patch.object(store,'save',side_effect=OSError('disk full')):
                with self.assertRaises(OSError): store.import_json(imp)
            self.assertEqual(store.items,[])
    def test_web_fragment_rejected(self):
        with self.assertRaises(ValueError):
            validate({**sample(), 'protocol':'WEB','host':'https://example.com/#frag'})
if __name__ == '__main__': unittest.main()
