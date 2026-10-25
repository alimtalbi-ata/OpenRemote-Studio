"""R103 Qt signal redaction test; synthetic client, no remote WinRM.
Author: Abdelhalim Talbi.
"""
import unittest
try:
    from PySide6.QtCore import QCoreApplication
    from winrm_inventory_qt import _InventoryJob
    from winrm_readonly import WinRMError
except ImportError:
    QCoreApplication = None

@unittest.skipIf(QCoreApplication is None, 'PySide6 unavailable; Windows Qt CI required')
class WinRMExceptionBoundaryQtR103Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])
    def test_untrusted_winrm_error_never_enters_signal(self):
        secret = 'R103_QT_SECRET_NEVER_SIGNAL'
        class Client:
            def __init__(self, *_args, **_kwargs):
                pass
            def inventory(self, *, online, cancelled):
                raise WinRMError(secret)
        job = _InventoryJob(42, 'https://windows.example.test', 'readonly',
                            'dummy-password', Client)
        received = []
        job.signals.finished.connect(lambda generation, result: received.append((generation, result)))
        job.run()
        self.assertEqual(received, [(42, {'state': 'error', 'code': 'winrm_transport_unavailable'})])
        self.assertNotIn(secret, repr(received))
        self.assertIsNone(job._password)

if __name__ == '__main__':
    unittest.main()
