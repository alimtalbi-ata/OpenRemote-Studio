import copy
import tempfile
import unittest
from pathlib import Path
from ssh_diagnostic_history import DiagnosticHistory
from ssh_history_integrity import create_export, verify_export

KEY = b'k'*32
REPORT = {'schema':'openremote.ssh-diagnostic.v1','status':'authenticated','steps':[{'step':'Bastion principal','state':'ok','duration_ms':120}]}
class HistoryIntegrityTests(unittest.TestCase):
    def record(self): return [{'recorded_at':123,'report':copy.deepcopy(REPORT)}]
    def test_roundtrip(self):
        self.assertEqual(verify_export(create_export(self.record(),KEY),KEY),self.record())
    def test_tamper_latency(self):
        doc=create_export(self.record(),KEY);doc['payload']['records'][0]['report']['steps'][0]['duration_ms']=999
        with self.assertRaises(ValueError):verify_export(doc,KEY)
    def test_wrong_key(self):
        with self.assertRaises(ValueError):verify_export(create_export(self.record(),KEY),b'z'*32)
    def test_no_raw_identity(self):
        row=self.record();row[0]['hostname']='sensitive.internal';row[0]['report']['password']='private'
        self.assertNotIn('sensitive.internal',str(create_export(row,KEY)))
        self.assertNotIn('private',str(create_export(row,KEY)))
    def test_short_key(self):
        with self.assertRaises(ValueError):create_export(self.record(),b'a')
    def test_noncanonical_payload(self):
        doc=create_export(self.record(),KEY);doc['payload']['records'][0]['report']['unexpected']='x'
        with self.assertRaises(ValueError):verify_export(doc,KEY)
    def test_bad_schema(self):
        doc=create_export(self.record(),KEY);doc['payload']['schema']='bad'
        with self.assertRaises(ValueError):verify_export(doc,KEY)
    def test_bad_time(self):
        with self.assertRaises(ValueError):create_export([{'recorded_at':-1,'report':REPORT}],KEY)
    def test_bounded(self):
        with self.assertRaises(ValueError):create_export(self.record()*201,KEY)
    def test_from_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            h=DiagnosticHistory(Path(tmp)/'history.db');h.add(REPORT)
            self.assertEqual(len(verify_export(create_export(h.recent(),KEY),KEY)),1)
