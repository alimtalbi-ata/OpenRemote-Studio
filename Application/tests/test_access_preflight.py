
import unittest
from access_preflight import inspect_access
class PreflightTests(unittest.TestCase):
 def test_direct_ssh(self):
  r=inspect_access({"protocol":"SSH"},{},which=lambda _: "/usr/bin/ssh",platform="posix")
  self.assertTrue(r["ready"])
 def test_missing_client(self):
  r=inspect_access({"protocol":"SSH"},{},which=lambda _: None,platform="posix")
  self.assertFalse(r["ready"])
 def test_windows_rdp(self):
  r=inspect_access({"protocol":"RDP"},{},which=lambda _: "mstsc.exe",platform="nt")
  self.assertTrue(r["ready"])
 def test_rdp_non_windows(self):
  r=inspect_access({"protocol":"RDP"},{},which=lambda _: "/bin/mstsc",platform="posix")
  self.assertFalse(r["ready"])
 def test_jump_sftp_warning(self):
  r=inspect_access({"protocol":"SFTP"},{"mode":"ssh_jump","jump_host":"bastion.example"},
      which=lambda _: "/bin/sftp",platform="posix")
  self.assertTrue(r["ready"])
  self.assertTrue(r["warnings"])
 def test_pam_reference_is_not_credential(self):
  r=inspect_access({"protocol":"RDP"},{"mode":"rd_gateway","gateway_host":"gw.example",
       "vault_ref":"PAM-123"},which=lambda _: "mstsc",platform="nt")
  self.assertFalse(r["ready"])
  self.assertTrue(any("PAM" in issue for issue in r["issues"]))
 def test_incompatible_route(self):
  r=inspect_access({"protocol":"RDP"},{"mode":"ssh_jump","jump_host":"jump"},
       which=lambda _: "mstsc",platform="nt")
  self.assertFalse(r["ready"])
