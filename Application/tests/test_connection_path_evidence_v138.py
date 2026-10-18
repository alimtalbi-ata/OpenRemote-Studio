import unittest
from connection_path_evidence import correlate,format_evidence
class EvidenceTests(unittest.TestCase):
    def test_empty(self):
        r=correlate('SSH');self.assertEqual(r['local']['assessment'],'aucune_tentative_locale');self.assertFalse(r['network_tested'])
    def test_failure_not_attributed(self):
        r=correlate('SSH',{'mode':'ssh_jump','jump_host':'private.example'},attempts=2,failures=1)
        self.assertFalse(r['hop_failure_confirmed']);self.assertTrue(all(n['status']=='non_verifie' for n in r['nodes']))
        self.assertNotIn('private.example',str(r))
    def test_unknown(self):
        self.assertEqual(correlate('RDP',attempts=2,unknown=1)['local']['assessment'],'fin_session_non_observee')
    def test_success_not_remote(self):
        self.assertIn('sans preuve de succès distant',format_evidence(correlate('VNC',attempts=1)))
    def test_local_readiness(self):
        r=correlate('SFTP',local_ready=False)
        self.assertEqual(r['nodes'][0]['status'],'prerequis_locaux_a_corriger')
        self.assertTrue(all(n['status']=='non_verifie' for n in r['nodes'][1:]))
    def test_bad_counts(self):
        for args in ({'attempts':1,'failures':2},{'attempts':-1},{'attempts':True}):
            with self.subTest(args=args),self.assertRaises(ValueError):correlate('SSH',**args)
    def test_bad_report(self):
        r=correlate('WEB');r['network_tested']=True
        with self.assertRaises(ValueError):format_evidence(r)
    def test_pam_redacted(self):
        r=correlate('RDP',{'mode':'direct','vault_ref':'secret-value'})
        self.assertIn('pam',[n['kind'] for n in r['nodes']]);self.assertNotIn('secret-value',str(r))
