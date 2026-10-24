"""R75: local-only filtering, privacy and fail-closed input validation."""
import copy
import unittest
from netbox_preview_filter import NetBoxFilterError, filter_preview


class NetBoxFilterR75Tests(unittest.TestCase):
    def setUp(self):
        self.result = {'state': 'ok', 'rows': [
            {'status': 'matched', 'device': 'PAR-SRV-01', 'local_host': '192.0.2.1', 'token': 'NEVER_EXPORT'},
            {'status': 'ambiguous', 'device': 'par-srv-02', 'local_host': ''},
            {'status': 'missing_local', 'device': 'LYON-SRV-01', 'local_host': ''},
            {'status': 'local_only', 'device': '', 'local_host': 'host.internal'}]}

    def test_all_rows_without_network(self):
        result = filter_preview(self.result)
        self.assertEqual((result['visible'], result['total']), (4, 4))

    def test_status_filter(self):
        result = filter_preview(self.result, status='ambiguous')
        self.assertEqual([r['device'] for r in result['rows']], ['par-srv-02'])

    def test_casefold_search_device(self):
        self.assertEqual(filter_preview(self.result, search='PAR-SRV')['visible'], 2)

    def test_search_local_host(self):
        self.assertEqual(filter_preview(self.result, search='HOST.INTERNAL')['rows'][0]['status'], 'local_only')

    def test_combined_status_and_search(self):
        self.assertEqual(filter_preview(self.result, status='matched', search='par')['visible'], 1)
        self.assertEqual(filter_preview(self.result, status='matched', search='lyon')['visible'], 0)

    def test_whitespace_only_search_matches_all(self):
        self.assertEqual(filter_preview(self.result, search='  ')['visible'], 4)

    def test_never_exposes_extra_fields_or_mutates(self):
        before = copy.deepcopy(self.result)
        self.assertNotIn('NEVER_EXPORT', repr(filter_preview(self.result)))
        self.assertEqual(before, self.result)

    def test_offline_and_error_refused(self):
        for state in ('offline', 'error'):
            with self.subTest(state=state), self.assertRaises(NetBoxFilterError):
                filter_preview({'state': state, 'rows': []})

    def test_unknown_status_rejected(self):
        with self.assertRaises(NetBoxFilterError):
            filter_preview(self.result, status='all\nsecret')

    def test_control_char_and_long_search_rejected(self):
        for search in ('secret\n', '\x00', 'a' * 121):
            with self.subTest(search=repr(search)), self.assertRaises(NetBoxFilterError):
                filter_preview(self.result, search=search)

    def test_malformed_row_refused_even_when_filtered_out(self):
        bad = {'state': 'ok', 'rows': self.result['rows'] + [{'status': 'matched', 'device': None, 'local_host': ''}]}
        with self.assertRaises(NetBoxFilterError):
            filter_preview(bad, status='ambiguous')

    def test_no_extra_field_access(self):
        class Guard(dict):
            def __getitem__(self, key):
                if key in ('password', 'token', 'user'):
                    raise AssertionError('credential read')
                return super().__getitem__(key)
        result = {'state': 'ok', 'rows': [Guard(status='matched', device='srv', local_host='host', token='SECRET')]}
        self.assertEqual(filter_preview(result)['visible'], 1)


if __name__ == '__main__':
    unittest.main()
