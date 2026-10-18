import copy,json,tempfile,unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from pam_lab_reports import make_report
from pam_audit_signatures import sign_report,verify_signed_report,verify_signed_files
class SignedAuditTests(unittest.TestCase):
 def setUp(self):
  self.private=Ed25519PrivateKey.generate()
  self.priv=self.private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
  self.pub=self.private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
  self.report=make_report([{'event':'DENY','target':'host'}])
 def test_valid_signature(self):
  sig=sign_report(self.report,self.priv)
  self.assertTrue(verify_signed_report(self.report,sig,self.pub))
 def test_tampered_report(self):
  sig=sign_report(self.report,self.priv)
  altered=copy.deepcopy(self.report);altered['events'][0]['event']['target']='other'
  self.assertFalse(verify_signed_report(altered,sig,self.pub))
 def test_wrong_public_key(self):
  sig=sign_report(self.report,self.priv)
  other=Ed25519PrivateKey.generate().public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
  self.assertFalse(verify_signed_report(self.report,sig,other))
 def test_signature_corruption(self):
  sig=sign_report(self.report,self.priv);sig['signature']='not base64'
  self.assertFalse(verify_signed_report(self.report,sig,self.pub))
 def test_refuses_unsigned_corrupt_report(self):
  broken=copy.deepcopy(self.report);broken['final_hash']='0'*64
  with self.assertRaises(ValueError):sign_report(broken,self.priv)
 def test_file_verification(self):
  sig=sign_report(self.report,self.priv)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'report.json').write_text(json.dumps(self.report));(p/'sig.json').write_text(json.dumps(sig));(p/'pub.pem').write_bytes(self.pub)
   self.assertTrue(verify_signed_files(p/'report.json',p/'sig.json',p/'pub.pem'))
 def test_oversized_signature_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'r').write_text('{}');(p/'s').write_bytes(b'a'*5000);(p/'k').write_bytes(self.pub)
   with self.assertRaises(ValueError):verify_signed_files(p/'r',p/'s',p/'k')
