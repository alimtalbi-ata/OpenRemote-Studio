import unittest
from ssh_transport import SSHSettings, create_ssh_client, guarded_ssh_session

class FakeClient:
    def __init__(self, fail=False): self.fail=fail; self.closed=False; self.calls=[]
    def load_system_host_keys(self): self.calls.append('system_keys')
    def load_host_keys(self,p): self.calls.append('known_hosts')
    def set_missing_host_key_policy(self,p): self.calls.append(type(p).__name__)
    def connect(self,**kwargs):
        self.calls.append(kwargs)
        if self.fail: raise OSError('network failed')
    def close(self): self.closed=True

class SSHTransportTests(unittest.TestCase):
    def test_reject_missing_settings(self):
        with self.assertRaises(ValueError): create_ssh_client(SSHSettings('', 'a'))
    def test_strict_hostkey_and_bounded_timeouts(self):
        c=FakeClient()
        result=create_ssh_client(SSHSettings('host','user',timeout=4), client_factory=lambda:c, policy_factory=object)
        self.assertIs(result,c)
        self.assertIn('system_keys',c.calls)
        self.assertEqual(c.calls[-1]['auth_timeout'],4)
        self.assertFalse(c.calls[-1]['allow_agent'])
    def test_failed_connect_closes_client(self):
        c=FakeClient(fail=True)
        with self.assertRaises(OSError): create_ssh_client(SSHSettings('host','user'),client_factory=lambda:c,policy_factory=object)
        self.assertTrue(c.closed)
    def test_guarded_adapter_close(self):
        c=FakeClient()
        adapter=guarded_ssh_session('id',SSHSettings('host','user'),client_factory=lambda:c,policy_factory=object)
        self.assertIs(adapter.connect(),c)
        adapter.close()
        self.assertTrue(c.closed)
    def test_missing_explicit_hostkeys_fail_closed_before_client_creation(self):
        created=[]
        def factory():
            created.append(True)
            return FakeClient()
        with self.assertRaises(FileNotFoundError):
            create_ssh_client(SSHSettings('host','user',known_hosts='/missing/ssh/known_hosts'),
                              client_factory=factory,policy_factory=object)
        self.assertEqual(created, [], 'missing trust material must fail before client creation')
if __name__=='__main__':unittest.main()
