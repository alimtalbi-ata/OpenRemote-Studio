"""R104: untrusted WinRM inventory text cannot spoof the operator's Qt view.
No network or secrets. Author: Abdelhalim Talbi.
"""
import unittest
from winrm_readonly import _text, _inventory, WinRMError
from winrm_services_readonly import _normalize_services

OS = {'Caption': 'Windows Server', 'Version': '10.0', 'BuildNumber': '20348', 'CSName': 'LAB-SRV'}
SERVICE = {'Name': 'Spooler', 'DisplayName': 'Print Spooler', 'State': 'Running', 'StartMode': 'Auto'}

class DisplayTrustR104(unittest.TestCase):
    def test_bidi_zero_width_c1_surrogate_and_separators_refused(self):
        for ch in ('\u202e', '\u2066', '\u200b', '\u0085', '\ud800', '\u2028', '\u2029', '\ufdd0', '\ufffe'):
            with self.subTest(codepoint=hex(ord(ch))):
                with self.assertRaisesRegex(WinRMError, '^winrm_invalid_response$'):
                    _text('safe' + ch + 'fake')

    def test_international_readable_text_remains_valid(self):
        self.assertEqual(_text('Service réseau — 日本語 / Español'), 'Service réseau — 日本語 / Español')

    def test_os_and_disk_remote_values_reject_bidi(self):
        for key in OS:
            payload = {'os': dict(OS), 'disks': []}
            payload['os'][key] += '\u202e'
            with self.subTest(key=key), self.assertRaisesRegex(WinRMError, '^winrm_invalid_response$'):
                _inventory(payload)

    def test_service_name_and_display_label_reject_invisible_controls(self):
        for key in ('Name', 'DisplayName'):
            row = dict(SERVICE)
            row[key] += '\u2066'
            with self.subTest(key=key), self.assertRaisesRegex(WinRMError, '^winrm_invalid_response$'):
                _normalize_services({'TotalCount': 1, 'Services': [row]})

    def test_valid_normalized_inventories_unchanged(self):
        self.assertEqual(_inventory({'os': OS, 'disks': [{'DeviceID': 'C:', 'Size': '10', 'FreeSpace': '3'}]})['disks'][0]['free_bytes'], 3)
        self.assertEqual(_normalize_services({'TotalCount': 1, 'Services': [SERVICE]})['services'][0]['name'], 'Spooler')

if __name__ == '__main__':
    unittest.main()
