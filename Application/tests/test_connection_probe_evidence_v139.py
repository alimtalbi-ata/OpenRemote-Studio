import unittest
from connection_probe_evidence import correlate_probes,format_probe_evidence
class ProbeEvidenceTests(unittest.TestCase):
 def test_empty(self):
  r=correlate_probes('SSH');self.assertEqual(r['status'],'aucune_preuve');self.assertFalse(r['hop_failure_confirmed'])
 def test_tcp_ok_not_remote_success(self):
  r=correlate_probes('RDP',records=[('tcp_local','ok')]);self.assertIn('non authentifié',format_probe_evidence(r))
 def test_tcp_failed_not_attributed(self):
  r=correlate_probes('SSH',{'mode':'ssh_jump','jump_host':'private.example'},[('tcp_local','failed')]);self.assertIsNone(r['events'][0]['hop_index']);self.assertNotIn('private.example',str(r))
 def test_ssh_failure_unknown_hop(self):
  r=correlate_probes('SSH',records=[('ssh_jump','failed')]);self.assertIn('saut inconnu',format_probe_evidence(r))
 def test_order(self):
  r=correlate_probes('SFTP',records=[('tcp_local','unknown'),('ssh_jump','unknown')]);self.assertEqual([e['kind'] for e in r['events']],['tcp_local','ssh_jump'])
 def test_invalid_kind(self):
  with self.assertRaises(ValueError):correlate_probes('SSH',records=[('secret','ok')])
 def test_invalid_outcome(self):
  with self.assertRaises(ValueError):correlate_probes('SSH',records=[('tcp_local','success')])
 def test_invalid_structure(self):
  with self.assertRaises(ValueError):correlate_probes('SSH',records=['abc'])
 def test_invalid_report(self):
  r=correlate_probes('SSH');r['hop_failure_confirmed']=True
  with self.assertRaises(ValueError):format_probe_evidence(r)
 def test_privacy(self):
  r=correlate_probes('RDP',{'mode':'direct','vault_ref':'secret-vault'},[('tcp_local','ok')]);self.assertNotIn('secret-vault',str(r))
