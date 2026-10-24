"""R98 local service drift tests: no WinRM, no network, no secrets."""
import unittest
from winrm_service_drift import ServiceDriftError, compare_service_snapshots


def row(name, state='Running', mode='Auto'):
    return {'name': name, 'display_name': name, 'state': state, 'start_mode': mode}


class DriftR98Tests(unittest.TestCase):
    def compare(self, old, new, old_cut=False, new_cut=False):
        return compare_service_snapshots(old, new, previous_truncated=old_cut,
                                         current_truncated=new_cut)

    def test_state_and_mode_transition(self):
        result = self.compare([row('Spooler')], [row('Spooler', 'Stopped', 'Disabled')])
        self.assertEqual(result['transitions'][0]['before_state'], 'Running')
        self.assertEqual(result['transitions'][0]['after_mode'], 'Disabled')

    def test_identical_snapshots_no_changes(self):
        result = self.compare([row('A')], [row('A')])
        self.assertEqual(result['transitions'], [])
        self.assertEqual(result['added'], [])

    def test_complete_membership_changes(self):
        result = self.compare([row('A')], [row('B')])
        self.assertEqual(result['added'], ['B'])
        self.assertEqual(result['removed'], ['A'])
        self.assertTrue(result['membership_complete'])

    def test_truncation_never_infers_membership_changes(self):
        for a, b in ((True, False), (False, True), (True, True)):
            with self.subTest(a=a, b=b):
                result = self.compare([row('A')], [row('B')], a, b)
                self.assertEqual((result['added'], result['removed']), ([], []))
                self.assertFalse(result['membership_complete'])

    def test_common_rows_still_compared_when_truncated(self):
        result = self.compare([row('A')], [row('A', 'Stopped')], True, True)
        self.assertEqual(len(result['transitions']), 1)

    def test_reject_duplicate_casefold_and_control(self):
        for bad in ([row('A'), row('a')], [row('bad\\nsecret')], [row('A', 'bogus')]):
            with self.subTest(bad=bad), self.assertRaisesRegex(ServiceDriftError, '^winrm_invalid_response$'):
                self.compare(bad, [])

    def test_reject_untrusted_extra_fields(self):
        bad = dict(row('A'), password='SECRET')
        with self.assertRaises(ServiceDriftError) as cm:
            self.compare([bad], [])
        self.assertNotIn('SECRET', str(cm.exception))

    def test_bound_and_boolean_validation(self):
        with self.assertRaises(ServiceDriftError):
            self.compare([row(str(i)) for i in range(129)], [])
        with self.assertRaises(ServiceDriftError):
            self.compare([], [], 1, False)


if __name__ == '__main__':
    unittest.main()
