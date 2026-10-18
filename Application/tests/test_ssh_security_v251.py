import tempfile
import unittest
from pathlib import Path
from ssh_security import CredentialRef, CredentialUnavailable, known_hosts_preflight, resolve_password
from ssh_transport import SSHSettings, create_ssh_client

class FakeClient:
    def __init__(self): self.closed=False; self.kw=None; self.hosts=None
    def load_host_keys(self,p): self.hosts=p
    def load_system_host_keys(self): pass
    def set_missing_host_key_policy(self,p): pass
    def connect(self,**kw): self.kw=kw
    def close(self): self.closed=True

class SecurityTests(unittest.TestCase):
    def test_credential_ref_rejects_blank(self):
        with self.assertRaises(ValueError): CredentialRef(' ')
    def test_provider_missing_fails_closed(self):
        with self.assertRaises(CredentialUnavailable): resolve_password(CredentialRef('x'),None)
    def test_provider_resolves_just_in_time(self):
        c=FakeClient(); seen=[]
        def provider(key): seen.append(key); return 'temporary-secret'
        result=create_ssh_client(SSHSettings('example','user'),credential_ref=CredentialRef('vault:one'),credential_provider=provider,client_factory=lambda:c,policy_factory=object)
        self.assertIs(result,c);self.assertEqual(seen,['vault:one']);self.assertEqual(c.kw['password'],'temporary-secret')
    def test_ambiguous_password_rejected(self):
        with self.assertRaises(ValueError): create_ssh_client(SSHSettings('example','user'),password='a',credential_ref=CredentialRef('b'))
    def test_explicit_empty_known_hosts_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'known_hosts';p.write_text('')
            with self.assertRaises(ValueError): known_hosts_preflight(str(p))
    def test_explicit_known_hosts_used(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'known_hosts';p.write_text('example ssh-ed25519 AAAA\n')
            c=FakeClient()
            create_ssh_client(SSHSettings('example','user',known_hosts=str(p)),client_factory=lambda:c,policy_factory=object)
            self.assertEqual(c.hosts,str(p))
if __name__=='__main__': unittest.main()
