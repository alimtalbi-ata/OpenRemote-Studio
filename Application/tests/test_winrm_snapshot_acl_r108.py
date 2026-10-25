"""R108: restricted Windows ACLs for per-request WinRM CA snapshots.

Pure SDDL contract tests run on all platforms. Native DACL tests run on Windows CI.
All credentials and endpoints in tests are synthetic; no remote network is used.
Author: Abdelhalim Talbi.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from winrm_readonly import (
    WinRMReadOnly,
    WinRMError,
    _sddl_is_private,
    _windows_current_user_sid,
    _read_windows_dacl_sddl,
    _windows_dacl_is_private,
    _create_windows_private_directory,
)
from winrm_services_readonly import WinRMServicesReadOnly

CA = Path(__file__).parent / "fixtures" / "r105-public-test-ca.pem"
ORIGIN = "https://windows.example.test"
TEST_SID = "S-1-5-21-111-222-333-1001"


class Reply:
    status_code = 0
    std_err = b""
    std_out = json.dumps({
        "os": {"Caption": "Windows", "Version": "10",
               "BuildNumber": "20348", "CSName": "LAB"},
        "disks": []
    }).encode()

    def run_ps(self, script):
        if "Win32_Service" in script:
            result = Reply()
            result.std_out = b'{"TotalCount":0,"Services":[]}'
            return result
        return self


class SnapshotACLContractR108(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.original = Path(self.temp.name) / "source.pem"
        self.original.write_bytes(CA.read_bytes())
        self.snapshots = []
        self.acl_records = []
        self.provider_calls = []
        self.factory_calls = []

    def factory(self, endpoint, username, password, *, timeout, ca_bundle=None):
        self.factory_calls.append(True)
        self.assertEqual(password, "FAKE_ONLY")
        self.assertIsNotNone(ca_bundle)
        snapshot = Path(ca_bundle)
        self.assertNotEqual(snapshot, self.original)
        self.assertTrue(snapshot.is_file())
        self.assertEqual(snapshot.read_bytes(), CA.read_bytes())
        if os.name == "nt":
            sid = _windows_current_user_sid()
            directory_sddl = _read_windows_dacl_sddl(str(snapshot.parent))
            file_sddl = _read_windows_dacl_sddl(str(snapshot))
            self.acl_records.append((sid, directory_sddl, file_sddl))
            self.assertTrue(_windows_dacl_is_private(
                str(snapshot.parent), sid, directory=True
            ))
            self.assertTrue(_windows_dacl_is_private(
                str(snapshot), sid, directory=False
            ))
        elif os.name == "posix":
            self.assertEqual(snapshot.stat().st_mode & 0o077, 0)
            self.assertEqual(snapshot.parent.stat().st_mode & 0o077, 0)
        self.snapshots.append(snapshot)
        return Reply()

    def provider(self):
        self.provider_calls.append(True)
        return "FAKE_ONLY"

    def client(self, cls=WinRMReadOnly, provider=None, factory=None):
        return cls(
            ORIGIN, "readonly", provider or self.provider,
            session_factory=factory or self.factory,
            ca_bundle=str(self.original.resolve())
        )

    def test_unresolved_local_admin_alias_is_not_assumed_to_be_current_user(self):
        # The pure parser never guesses that a variable SDDL alias is the
        # supplied process SID. Only the Windows API resolver can canonicalize
        # LA, preventing a domain Administrator with RID 500 from being confused
        # with the machine's local Administrator.
        unresolved = "D:P(A;OICI;FA;;;LA)(A;OICI;FA;;;SY)"
        self.assertFalse(_sddl_is_private(
            unresolved, TEST_SID, directory=True
        ))

    def test_only_explicit_user_and_system_aces_are_accepted(self):
        directory_sddl = (
            f"D:P(A;OICI;FA;;;{TEST_SID})(A;OICI;FA;;;SY)"
        )
        file_sddl = f"D:AI(A;ID;FA;;;{TEST_SID})(A;ID;FA;;;SY)"
        self.assertTrue(_sddl_is_private(
            directory_sddl, TEST_SID, directory=True
        ))
        self.assertTrue(_sddl_is_private(file_sddl, TEST_SID, directory=False))

    def test_unprotected_broad_extra_or_inherit_only_aces_are_rejected(self):
        sddl_without_protected_dacl = (
            f"D:(A;OICI;FA;;;{TEST_SID})(A;OICI;FA;;;SY)"
        )
        sddl_with_everyone = (
            f"D:P(A;OICI;FA;;;{TEST_SID})(A;OICI;FA;;;SY)"
            "(A;OICI;FA;;;WD)"
        )
        sddl_file_inherit_only = (
            f"D:AI(A;IDIO;FA;;;{TEST_SID})(A;ID;FA;;;SY)"
        )
        self.assertFalse(_sddl_is_private(
            sddl_without_protected_dacl, TEST_SID, directory=True
        ))
        self.assertFalse(_sddl_is_private(
            sddl_with_everyone, TEST_SID, directory=True
        ))
        self.assertFalse(_sddl_is_private(
            sddl_file_inherit_only, TEST_SID, directory=False
        ))

    def test_acl_setup_failure_precedes_credentials_for_inventory_and_services(self):
        for cls, method in (
            (WinRMReadOnly, "inventory"),
            (WinRMServicesReadOnly, "services"),
        ):
            with self.subTest(client=cls.__name__):
                self.provider_calls.clear()
                self.factory_calls.clear()
                client = self.client(cls)
                with patch(
                    "winrm_readonly._private_snapshot_directory",
                    side_effect=WinRMError("winrm_snapshot_acl_failed"),
                ):
                    with self.assertRaisesRegex(
                        WinRMError, "^winrm_snapshot_acl_failed$"
                    ):
                        getattr(client, method)(online=True)
                self.assertEqual(self.provider_calls, [])
                self.assertEqual(self.factory_calls, [])

    @unittest.skipUnless(os.name == "nt", "native Windows DACL integration")
    def test_windows_created_directory_dacl_round_trip(self):
        # Bypass only the creator's in-function assertion so that a Windows
        # runner can independently expose whether the DACL read-back/parser
        # contract matches the actual NTFS descriptor. This test then validates
        # the real descriptor with the production pure parser.
        from winrm_readonly import _sddl_is_private
        with patch("winrm_readonly._windows_dacl_is_private", return_value=True):
            directory, sid = _create_windows_private_directory()
        try:
            sddl = _read_windows_dacl_sddl(directory)
            self.assertNotIn(";;;LA)", sddl)  # OS alias resolved to exact numeric SID
            diagnostic = sddl.replace(sid, "<CURRENT_USER_SID>")
            self.assertTrue(
                _sddl_is_private(sddl, sid, directory=True),
                "Windows-created DACL did not match the strict contract: " + diagnostic
            )
        finally:
            try:
                os.rmdir(directory)
            except OSError:
                pass

    @unittest.skipUnless(os.name == "nt", "native Windows DACL integration")
    def test_windows_native_snapshot_dacl_for_inventory_and_services(self):
        inventory = self.client().inventory(online=True)
        services = self.client(WinRMServicesReadOnly).services(online=True)
        self.assertEqual(inventory["state"], "ok")
        self.assertEqual(services["services"], [])
        self.assertEqual(len(self.acl_records), 2)
        for sid, directory_sddl, file_sddl in self.acl_records:
            self.assertTrue(directory_sddl.startswith("D:P"))
            self.assertIn(sid, directory_sddl)
            self.assertIn(sid, file_sddl)
            self.assertTrue(_sddl_is_private(
                directory_sddl, sid, directory=True
            ))
            self.assertTrue(_sddl_is_private(
                file_sddl, sid, directory=False
            ))
        self.assertTrue(all(not path.exists() for path in self.snapshots))
        self.assertTrue(all(not path.parent.exists() for path in self.snapshots))


if __name__ == "__main__":
    unittest.main()
