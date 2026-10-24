"""R97 precise service inventory total: real pure-Python contract tests.
Author: Abdelhalim Talbi.
"""
import json
import unittest
from winrm_service_totals import (
    MAX_SERVICES, ServiceTotalError, unwrap_service_envelope,
    validated_display_total,
)
from winrm_services_readonly import WinRMServicesReadOnly
from winrm_readonly import WinRMError


def service(name):
    return {'Name': name, 'DisplayName': name, 'State': 'Running', 'StartMode': 'Auto'}


class FakeSession:
    def __init__(self, raw):
        self.raw = raw
        self.scripts = []
    def __call__(self, *args, **kwargs):
        return self
    def run_ps(self, script):
        self.scripts.append(script)
        return type('Reply', (), {'status_code': 0, 'std_out': json.dumps(self.raw).encode()})()


class ServiceTotalsR97Tests(unittest.TestCase):
    def test_exact_128_is_complete(self):
        rows = [{} for _ in range(MAX_SERVICES)]
        count, parsed = unwrap_service_envelope({'TotalCount': 128, 'Services': rows})
        self.assertEqual(count, 128)
        self.assertEqual(len(parsed), 128)
        self.assertEqual(validated_display_total(count, parsed, False), 128)

    def test_129_is_truncated(self):
        rows = [{} for _ in range(MAX_SERVICES)]
        count, parsed = unwrap_service_envelope({'TotalCount': 129, 'Services': rows})
        self.assertEqual(validated_display_total(count, parsed, True), 129)

    def test_empty_and_singleton(self):
        self.assertEqual(unwrap_service_envelope({'TotalCount': 0, 'Services': []}), (0, []))
        self.assertEqual(unwrap_service_envelope({'TotalCount': 1, 'Services': {'Name': 'A'}}),
                         (1, [{'Name': 'A'}]))
        self.assertEqual(unwrap_service_envelope({'TotalCount': 0, 'Services': None}), (0, []))

    def test_legacy_payload_has_unknown_total(self):
        self.assertEqual(unwrap_service_envelope([]), (None, []))
        self.assertEqual(unwrap_service_envelope({'Name': 'Spooler'}),
                         (None, {'Name': 'Spooler'}))
        self.assertIsNone(validated_display_total(None, [], False))

    def test_bad_counts_fail_closed(self):
        rows = [{} for _ in range(MAX_SERVICES)]
        bad = [
            {'TotalCount': True, 'Services': []},
            {'TotalCount': -1, 'Services': []},
            {'TotalCount': 1_000_001, 'Services': rows},
            {'TotalCount': 129, 'Services': [{}]},
            {'TotalCount': 127, 'Services': rows},
            {'TotalCount': 0, 'Services': [], 'Password': 'secret'},
            {'TotalCount': '128', 'Services': rows},
        ]
        for value in bad:
            with self.subTest(value=str(value)[:70]), self.assertRaisesRegex(
                    ServiceTotalError, '^winrm_invalid_response$'):
                unwrap_service_envelope(value)

    def test_ui_rejects_forged_truncation(self):
        rows = [{} for _ in range(128)]
        for total, truncated in ((128, True), (129, False), (127, False),
                                 (True, False), (1_000_001, True)):
            with self.subTest(total=total, truncated=truncated), self.assertRaises(ServiceTotalError):
                validated_display_total(total, rows, truncated)

    def test_no_untrusted_values_in_error(self):
        with self.assertRaises(ServiceTotalError) as cm:
            unwrap_service_envelope({'TotalCount': 'PASSWORD-SECRET', 'Services': []})
        self.assertEqual(str(cm.exception), 'winrm_invalid_response')

    def test_backend_exact_count_and_fixed_query(self):
        rows = [service('S' + str(i)) for i in range(128)]
        for total, truncated in ((128, False), (129, True)):
            fake = FakeSession({'TotalCount': total, 'Services': rows})
            client = WinRMServicesReadOnly('https://win.example.test', 'reader',
                                            lambda: 'TEST-PASSWORD', session_factory=fake)
            result = client.services(online=True)
            self.assertEqual(result['total_count'], total)
            self.assertEqual(result['may_be_truncated'], truncated)
            self.assertEqual(len(result['services']), 128)
            self.assertIn('TotalCount = $all.Count', fake.scripts[0])
            self.assertNotIn('TEST-PASSWORD', fake.scripts[0])

    def test_backend_rejects_mismatched_envelope(self):
        fake = FakeSession({'TotalCount': 3, 'Services': [service('One')]})
        client = WinRMServicesReadOnly('https://win.example.test', 'reader',
                                        lambda: 'TEST-PASSWORD', session_factory=fake)
        with self.assertRaisesRegex(WinRMError, '^winrm_invalid_response$'):
            client.services(online=True)


if __name__ == '__main__':
    unittest.main()
