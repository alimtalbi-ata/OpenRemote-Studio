"""R104 Qt contract: reject untrusted custom adapter payloads before rendering."""
import unittest
try:
    from PySide6.QtWidgets import QApplication
    from winrm_inventory_qt import WinRMInventoryPanel, WinRMServicesPanel
except ImportError:
    QApplication = None

@unittest.skipIf(QApplication is None, 'PySide6 unavailable: Windows Qt CI required')
class DisplayTrustQtR104(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_service_bidi_payload_refused_before_tree_render(self):
        panel = WinRMServicesPanel()
        try:
            panel.consent.setChecked(True)
            payload = {'state': 'ok', 'read_only': True, 'limit': 128,
                       'may_be_truncated': False, 'total_count': 1,
                       'services': [{'name': 'Spoo\u202eler', 'display_name': 'Printer',
                                     'state': 'Running', 'start_mode': 'Auto'}]}
            panel._finished(panel._generation, payload)
            self.assertEqual(panel.table.topLevelItemCount(), 0)
            self.assertEqual(panel.status.text(), 'Réponse WinRM invalide.')
        finally:
            panel.close()

    def test_os_untrusted_payload_refused_before_tree_render(self):
        panel = WinRMInventoryPanel()
        try:
            panel.consent.setChecked(True)
            payload = {'state': 'ok', 'read_only': True,
                       'os': {'caption': 'Windows\u2066fake', 'version': '10.0',
                              'build': '20348', 'computer': 'LAB'}, 'disks': []}
            panel._finished(panel._generation, payload)
            self.assertEqual(panel.table.topLevelItemCount(), 0)
            self.assertEqual(panel.status.text(), 'Réponse WinRM invalide.')
        finally:
            panel.close()

    def test_invalid_disk_size_rejected_even_if_custom_adapter_returns_ok(self):
        panel = WinRMInventoryPanel()
        try:
            panel.consent.setChecked(True)
            payload = {'state': 'ok', 'read_only': True,
                       'os': {'caption': 'Windows', 'version': '10.0',
                              'build': '20348', 'computer': 'LAB'},
                       'disks': [{'drive': 'C:', 'size_bytes': 3, 'free_bytes': 4}]}
            panel._finished(panel._generation, payload)
            self.assertEqual(panel.table.topLevelItemCount(), 0)
            self.assertEqual(panel.status.text(), 'Réponse WinRM invalide.')
        finally:
            panel.close()

if __name__ == '__main__':
    unittest.main()
