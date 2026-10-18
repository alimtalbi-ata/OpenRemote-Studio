import unittest,json
from ssh_diagnostic_compare import compare_reports,compare_with_result
from ssh_diagnostic_report import summarize

class TestV99(unittest.TestCase):
    def report(self,ms=20,state='ok'):
        return {'schema':'openremote.ssh-diagnostic.v1','status':'authenticated' if state=='ok' else 'failed',
                'steps':[{'step':'Bastion principal','state':state,'duration_ms':ms}]}
    def test_duration_delta(self):self.assertEqual(compare_reports(self.report(20),self.report(35))['steps'][0]['delta_ms'],15)
    def test_improvement(self):self.assertEqual(compare_reports(self.report(40),self.report(10))['steps'][0]['delta_ms'],-30)
    def test_status_change(self):self.assertEqual(compare_reports(self.report(10,'failed'),self.report(12))['steps'][0]['previous_state'],'failed')
    def test_missing_step(self):
        r=self.report();r['steps']=[]
        self.assertIsNone(compare_reports(r,self.report())['steps'][0]['delta_ms'])
    def test_json_string(self):self.assertEqual(len(compare_reports(json.dumps(self.report()),self.report())['steps']),1)
    def test_reject_host_injection(self):
        r=self.report();r['steps'][0]['step']='admin@secret.example'
        with self.assertRaises(ValueError):compare_reports(r,self.report())
    def test_reject_invalid_duration(self):
        r=self.report();r['steps'][0]['duration_ms']=True
        with self.assertRaises(ValueError):compare_reports(r,self.report())
    def test_reject_wrong_schema(self):
        r=self.report();r['schema']='unknown'
        with self.assertRaises(ValueError):compare_reports(r,self.report())
    def test_reject_large_json(self):
        with self.assertRaises(ValueError):compare_reports(' '*65537,self.report())
    def test_current_result(self):
        result={'status':'authenticated','events':[{'step':'Bastion principal','state':'ok','duration_ms':25}]}
        self.assertEqual(compare_with_result(self.report(20),result)['steps'][0]['delta_ms'],5)
