"""R105 real PEM parsing and fail-closed CA trust tests (offline)."""
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from winrm_readonly import WinRMReadOnly, WinRMError, _pywinrm_session, validate_ca_bundle
from winrm_services_readonly import WinRMServicesReadOnly
CA = Path(__file__).parent / 'fixtures' / 'r105-public-test-ca.pem'
ORIGIN = 'https://windows.example.test'
class Reply:
    status_code = 0
    std_err = b''
    std_out = json.dumps({'os': {'Caption': 'Windows', 'Version': '10',
                       'BuildNumber': '20348', 'CSName': 'LAB'}, 'disks': []}).encode()
class Transport:
    def __init__(self): self.calls = []
    def __call__(self, endpoint, username, password, *, timeout, ca_bundle=None):
        self.calls.append((endpoint, username, password, timeout, ca_bundle))
        return self
    def run_ps(self, script):
        if 'Win32_Service' in script:
            r = Reply()
            r.std_out = b'{"TotalCount":0,"Services":[]}'
            return r
        return Reply()
class CABundleR105(unittest.TestCase):
    def test_valid_real_pem(self):
        self.assertEqual(validate_ca_bundle(str(CA.resolve())), str(CA.resolve()))
        self.assertIsNone(validate_ca_bundle(None))
    def test_invalid_files_and_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = root/'bad.pem'; bad.write_text('NOT A CERTIFICATE')
            big = root/'big.pem'; big.write_bytes(b'x'*(1048576+1))
            directory = root/'dir'; directory.mkdir()
            for value in ('relative.pem','\n/tmp/evil.pem',str(bad),str(big),
                          str(directory),str(root/'missing.pem'),'\\\\server\\share\\ca.pem'):
                with self.subTest(value=value),self.assertRaisesRegex(WinRMError,'^winrm_invalid_ca_bundle$'):
                    validate_ca_bundle(value)
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp)/'link.pem'
            try: link.symlink_to(CA)
            except (OSError,NotImplementedError): self.skipTest('symlink unavailable')
            with self.assertRaisesRegex(WinRMError,'^winrm_invalid_ca_bundle$'):
                validate_ca_bundle(str(link))
    def test_invalid_bundle_blocks_secrets_and_transport(self):
        calls=[]
        with self.assertRaisesRegex(WinRMError,'^winrm_invalid_ca_bundle$'):
            WinRMReadOnly(ORIGIN,'reader',lambda:calls.append('secret'),
                          session_factory=lambda *a,**kw:calls.append('network'),
                          ca_bundle='/missing/r105.pem')
        self.assertEqual(calls,[])
    def test_inventory_ca_and_offline(self):
        transport=Transport()
        client=WinRMReadOnly(ORIGIN,'reader',lambda:'TEST_PASSWORD',
                             session_factory=transport,ca_bundle=str(CA.resolve()))
        self.assertEqual(client.inventory()['state'],'offline')
        self.assertEqual(transport.calls,[])
        self.assertEqual(client.inventory(online=True)['state'],'ok')
        self.assertEqual(transport.calls[0][-1],str(CA.resolve()))
    def test_services_ca(self):
        transport=Transport()
        client=WinRMServicesReadOnly(ORIGIN,'reader',lambda:'TEST_PASSWORD',
                                     session_factory=transport,ca_bundle=str(CA.resolve()))
        self.assertEqual(client.services(online=True)['services'],[])
        self.assertEqual(transport.calls[0][-1],str(CA.resolve()))
    def test_pywinrm_keeps_tls_validation(self):
        calls=[]
        fake=types.SimpleNamespace(Session=lambda *a,**kw:calls.append(kw))
        with patch.dict(sys.modules,{'winrm':fake}):
            _pywinrm_session('https://host:5986/wsman','reader','secret',timeout=30)
            _pywinrm_session('https://host:5986/wsman','reader','secret',
                             timeout=30,ca_bundle=str(CA.resolve()))
        self.assertNotIn('ca_trust_path',calls[0])
        self.assertEqual(calls[1]['ca_trust_path'],str(CA.resolve()))
        for kw in calls:
            self.assertEqual(kw['server_cert_validation'],'validate')
            self.assertEqual(kw['transport'],'ntlm')
    def test_error_never_exposes_path(self):
        with self.assertRaisesRegex(WinRMError,'^winrm_invalid_ca_bundle$') as ctx:
            validate_ca_bundle('/private/username/password-ca.pem')
        self.assertNotIn('private',str(ctx.exception))
if __name__=='__main__':unittest.main()
