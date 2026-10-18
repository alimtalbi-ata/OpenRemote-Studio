import unittest
from pathlib import Path

class NetworkCancelContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code=(Path(__file__).resolve().parents[1]/'app.py').read_text()
    def test_sftp_transfer_checks_cancellation(self):
        self.assertIn("if scope.cancelled:return\n                from sftp_atomic_transfer import download_atomic",self.code)
        self.assertIn("if scope.cancelled:return\n                from sftp_atomic_upload import upload_atomic",self.code)
    def test_sftp_listing_checks_cancellation(self):
        self.assertIn("if scope.cancelled:return\n                entries=s.listdir_attr(folder)",self.code)
    def test_tunnel_start_checks_cancellation(self):
        self.assertIn("if scope.cancelled:return\n                    tunnel.start()",self.code)
