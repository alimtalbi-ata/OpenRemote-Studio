import unittest
from ssh_hop_probe import plan,check,classify_probe

H=[{'host':'jump1.example.org','port':22,'user':'ops'}, {'host':'jump2.example.org','port':2222,'user':'admin'}]

class ProbeTests(unittest.TestCase):
    def test_plan(self):
        p=plan(H);self.assertEqual([x['index'] for x in p],[1,2]);self.assertEqual(p[1]['port'],2222)
    def test_success_no_ssh_claim(self):
        class Socket:
            def close(self):pass
        result=check(H,connector=lambda address,timeout:Socket())
        self.assertEqual([x['status'] for x in result],['tcp_open_local']*2)
        self.assertIn('NON vérifiés',result[0]['message'])
    def test_failure_isolated(self):
        class Socket:
            def close(self):pass
        def connect(addr,timeout):
            if addr[1]==22:raise ConnectionRefusedError('secret')
            return Socket()
        result=check(H,connector=connect)
        self.assertEqual(result[0]['status'],'tcp_unavailable_local')
        self.assertEqual(result[1]['status'],'tcp_open_local')
        self.assertNotIn('secret',str(result))
    def test_invalid_timeout(self):
        for timeout in (0,6,True,'2'):
            with self.assertRaises(ValueError):check(H,timeout=timeout)
    def test_invalid_path(self):
        with self.assertRaises(ValueError):plan(H+H)
    def test_invalid_index(self):
        with self.assertRaises(ValueError):classify_probe(0,True)
    def test_indeterminate(self):
        self.assertEqual(classify_probe(1,None)['status'],'tcp_unknown_local')
    def test_no_passwords(self):
        with self.assertRaises(ValueError):plan([{'host':'example.org','user':'user:secret','port':22}])
