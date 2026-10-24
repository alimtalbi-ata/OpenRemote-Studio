"""Qt SFTP worker regression tests using an in-memory fake connection."""
import stat
import unittest
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication
from qt_workers import SftpJob


class FakeSftp:
    def __init__(self, on_list=None):
        self.on_list = on_list

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def listdir_attr(self, path):
        if self.on_list:
            self.on_list()
        return [type('Entry', (), {'filename': 'data', 'st_mode': stat.S_IFREG, 'st_size': 4})()]


class FakeClient:
    def __init__(self, sftp, close_raises=False):
        self.sftp = sftp
        self.close_raises = close_raises
        self.closed = False

    def open_sftp(self):
        return self.sftp

    def close(self):
        self.closed = True
        if self.close_raises:
            raise OSError('close failed')


class SftpWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_cancel_before_connection_does_not_open_socket(self):
        attempts = []
        def connect(_):
            attempts.append(True)
            raise AssertionError('Connection should not be attempted')
        job = SftpJob(connect, {'id': 'test'}, 'list', '.', None)
        success, errors = [], []
        job.signals.finished.connect(success.append)
        job.signals.failed.connect(errors.append)
        job.cancel()
        job.run()
        self.assertFalse(attempts)
        self.assertFalse(success)
        self.assertEqual(len(errors), 1)
        self.assertIn('InterruptedError', errors[0])

    def test_connection_failure_reports_error(self):
        def connect(_):
            raise OSError('Connection refused')
        job = SftpJob(connect, {'id': 'test'}, 'list', '.', None)
        success, errors = [], []
        job.signals.finished.connect(success.append)
        job.signals.failed.connect(errors.append)
        job.run()
        self.assertFalse(success)
        self.assertEqual(len(errors), 1)
        self.assertIn('Connection refused', errors[0])

    def test_listing_returns_result(self):
        client = FakeClient(FakeSftp())
        job = SftpJob(lambda _: client, {'id': 'test'}, 'list', '.', None)
        success, errors = [], []
        job.signals.finished.connect(success.append)
        job.signals.failed.connect(errors.append)
        job.run()
        self.assertEqual(success, [[('data', False, 4)]])
        self.assertFalse(errors)
        self.assertTrue(client.closed)

    def test_listing_missing_server_metadata_does_not_fail(self):
        client = FakeClient(FakeSftp())
        def list_missing_metadata(_):
            return [type('Entry', (), {
                'filename': 'unknown', 'st_mode': None, 'st_size': None
            })()]
        client.sftp.listdir_attr = list_missing_metadata
        job = SftpJob(lambda _: client, {'id': 'test'}, 'list', '.', None)
        success, errors = [], []
        job.signals.finished.connect(success.append)
        job.signals.failed.connect(errors.append)
        job.run()
        self.assertEqual(success, [[('unknown', False, None)]])
        self.assertFalse(errors)
        self.assertTrue(client.closed)

    def test_cancel_during_listing_never_reports_success(self):
        client = FakeClient(FakeSftp())
        job = SftpJob(lambda _: client, {'id': 'test'}, 'list', '.', None)
        client.sftp.on_list = job.cancel
        success, errors = [], []
        job.signals.finished.connect(success.append)
        job.signals.failed.connect(errors.append)
        job.run()
        self.assertFalse(success)
        self.assertEqual(len(errors), 1)
        self.assertIn('InterruptedError', errors[0])
        self.assertTrue(client.closed)

    def test_cancel_after_transfer_does_not_report_success(self):
        client = FakeClient(FakeSftp())
        job = SftpJob(lambda _: client, {'id': 'test'}, 'upload',
                      './remote.bin', './local.bin')
        success, errors = [], []
        job.signals.finished.connect(success.append)
        job.signals.failed.connect(errors.append)

        def upload_then_cancel(*args, **kwargs):
            job.cancel()
            return 4

        with patch('qt_workers.upload_exclusive', side_effect=upload_then_cancel) as upload:
            job.run()
        upload.assert_called_once()
        self.assertFalse(success)
        self.assertEqual(len(errors), 1)
        self.assertIn('InterruptedError', errors[0])
        self.assertTrue(client.closed)

    def test_transfer_error_reports_failure_and_closes_client(self):
        client = FakeClient(FakeSftp())
        job = SftpJob(lambda _: client, {'id': 'test'}, 'download',
                      './remote.bin', './local.bin')
        success, errors = [], []
        job.signals.finished.connect(success.append)
        job.signals.failed.connect(errors.append)
        with patch('qt_workers.download_atomic', side_effect=OSError('transfer failed')):
            job.run()
        self.assertFalse(success)
        self.assertEqual(len(errors), 1)
        self.assertIn('transfer failed', errors[0])
        self.assertTrue(client.closed)

    def test_cleanup_failure_does_not_escape_worker(self):
        client = FakeClient(FakeSftp(), close_raises=True)
        job = SftpJob(lambda _: client, {'id': 'test'}, 'list', '.', None)
        success = []
        job.signals.finished.connect(success.append)
        job.run()
        self.assertEqual(len(success), 1)
        self.assertTrue(client.closed)


if __name__ == '__main__':
    unittest.main()
