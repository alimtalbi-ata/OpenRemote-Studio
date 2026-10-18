import unittest
from reliability_metrics import enrich_statistics,filter_statistics

class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.rows=[dict(name='Linux A',protocol='SSH',attempts=4,observed=2,success=1,failed=1,unobserved=2),dict(name='RDS',protocol='RDP',attempts=2,observed=0,success=0,failed=0,unobserved=2)]
    def test_denominator_observed_only(self):
        a=enrich_statistics(self.rows)[0]
        self.assertEqual(a['local_zero_exit_rate'],50.0)
        self.assertEqual(a['observation_rate'],50.0)
    def test_unknown_is_not_success(self):
        b=enrich_statistics(self.rows)[1]
        self.assertIsNone(b['local_zero_exit_rate'])
        self.assertEqual(b['risk'],'Données insuffisantes')
    def test_filter_casefold(self):
        self.assertEqual(len(filter_statistics(enrich_statistics(self.rows),'linux')),1)
    def test_only_failures(self):
        self.assertEqual(len(filter_statistics(enrich_statistics(self.rows),only_failures=True)),1)
    def test_empty_data(self):
        self.assertEqual(enrich_statistics([]),[])
