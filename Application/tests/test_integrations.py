import unittest
from integrations import TOOLS, discover, filter_tools

class IntegrationTests(unittest.TestCase):
    def test_discovery_no_process(self):
        calls=[]
        def which(name):
            calls.append(name)
            return '/fake/docker' if name=='docker' else None
        result=discover(which)
        self.assertEqual(len(result),len(TOOLS))
        self.assertTrue(next(t for t in result if t['name']=='Docker')['available'])
        self.assertFalse(next(t for t in result if t['name']=='Kubernetes')['available'])
        self.assertIn('docker',calls)
    def test_filter(self):
        self.assertEqual([x['name'] for x in filter_tools('KUBERNETES',discover(lambda _:None))],['Kubernetes','Helm'])
    def test_paths_not_commands(self):
        result=discover(lambda _:None)
        self.assertTrue(all(not x['path'] and not x['available'] for x in result))
