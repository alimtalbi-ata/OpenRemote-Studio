import unittest,json
from ssh_end_to_end_probe import probe
from ssh_diagnostic_report import summarize,export_json
from ssh_diagnostic_view import stage_rows

class FakeClient:
    def __init__(self,endpoint,route,on_stage,**kwargs):self.callback=on_stage;self.closed=False
    def connect(self):
        self.callback('bastion_connect','starting')
        self.callback('bastion_connect','ok')
        self.callback('target_connect','starting')
        self.callback('target_connect','ok')
    def close(self):self.closed=True

class TestV98(unittest.TestCase):
    def result(self):
        ticks=iter([1.,1.125,2.,2.250])
        return probe([{'host':'jump.example','port':22,'user':'admin'}],'target.example',factory=FakeClient,consent=True,clock=lambda:next(ticks))
    def test_durations(self):self.assertEqual([e['duration_ms'] for e in self.result()['events'] if 'duration_ms' in e],[125,250])
    def test_summary(self):self.assertEqual(summarize(self.result())['total_measured_ms'],375)
    def test_anonymized(self):
        data=export_json(self.result())
        self.assertNotIn('jump.example',data);self.assertNotIn('target.example',data);self.assertNotIn('admin',data)
    def test_valid_json(self):self.assertEqual(json.loads(export_json(self.result()))['schema'],'openremote.ssh-diagnostic.v1')
    def test_invalid_duration(self):
        with self.assertRaises(ValueError):stage_rows([{'step':'Serveur cible','state':'ok','duration_ms':-1}])
    def test_bool_duration(self):
        with self.assertRaises(ValueError):stage_rows([{'step':'Serveur cible','state':'ok','duration_ms':True}])
    def test_no_raw_exception(self):
        with self.assertRaises(ValueError):summarize({'status':'unknown','events':[]})
    def test_failed_step(self):
        report=summarize({'status':'failed','events':[{'step':'Bastion principal','state':'failed','duration_ms':12}]})
        self.assertEqual(report['failed_step'],'Bastion principal')
    def test_cancelled(self):self.assertEqual(summarize({'status':'cancelled','events':[]})['steps'][-1]['state'],'cancelled')
