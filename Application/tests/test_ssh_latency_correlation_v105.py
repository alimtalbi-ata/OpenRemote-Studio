import unittest
from ssh_latency_correlation import correlate
from ssh_latency_alerts import STEPS


def sample(values):
    return [{'recorded_at':i,'duration_ms':v} for i,v in enumerate(values)]

class CorrelationTests(unittest.TestCase):
    def test_empty(self):
        self.assertFalse(correlate({'series':{}})['multi_step_degradation'])
    def test_multi_step(self):
        result=correlate({'series':{STEPS[0]:sample([100,110,600]),STEPS[1]:sample([90,95,700])}})
        self.assertTrue(result['multi_step_degradation'])
    def test_single_step(self):
        self.assertFalse(correlate({'series':{STEPS[0]:sample([100,110,600])}})['multi_step_degradation'])
    def test_recurrence(self):
        self.assertIn(STEPS[0],correlate({'series':{STEPS[0]:sample([700,100,800,100,900])}})['recurrent_steps'])
    def test_no_recurrence(self):
        self.assertFalse(correlate({'series':{STEPS[0]:sample([100,100,800,100,900])}})['recurrent_steps'])
    def test_short_history(self):
        self.assertFalse(correlate({'series':{STEPS[0]:sample([800,900])}})['recurrent_steps'])
    def test_bad_windows(self):
        for w,r in ((2,2),(5,6),(True,2),(5,1)):
            with self.subTest(w=w,r=r),self.assertRaises(ValueError):correlate({'series':{}},window=w,recurrence=r)
    def test_bad_timestamp(self):
        with self.assertRaises(ValueError):correlate({'series':{STEPS[0]:[{'recorded_at':'now','duration_ms':2}]}})
    def test_out_of_order(self):
        with self.assertRaises(ValueError):correlate({'series':{STEPS[0]:[{'recorded_at':2,'duration_ms':1},{'recorded_at':1,'duration_ms':2}]}})
    def test_invalid_measure(self):
        with self.assertRaises(ValueError):correlate({'series':{STEPS[0]:sample([float('nan')])}})
    def test_no_identity_leak(self):
        result=correlate({'series':{STEPS[0]:sample([100,110,700])}})
        self.assertNotIn('hostname',str(result))
