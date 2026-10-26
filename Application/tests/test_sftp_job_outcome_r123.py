"""R123 SFTP worker terminal outcome and cleanup order regressions.

Windows native/cumulative CI provides PySide6. A Qt-free lane skips this file
instead of claiming the worker integration was executed.
"""
import stat
import unittest
from types import SimpleNamespace

try:
    import PySide6  # noqa: F401
except ImportError:
    SftpJob = None
else:
    from qt_workers import SftpJob


class FakeSftp:
    def __init__(self, before_list=None, list_error=None):
        self.before_list = before_list
        self.list_error = list_error
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True
        return False

    def listdir_attr(self, _path):
        if self.before_list is not None:
            self.before_list()
        if self.list_error is not None:
            raise self.list_error
        return [SimpleNamespace(filename="sample.txt", st_mode=stat.S_IFREG, st_size=7)]


class FakeClient:
    def __init__(self, sftp):
        self.sftp = sftp
        self.close_attempted = False

    def open_sftp(self):
        return self.sftp

    def close(self):
        self.close_attempted = True


@unittest.skipIf(SftpJob is None, "PySide6 unavailable; Windows native/cumulative CI required")
class SftpJobOutcomeR123Tests(unittest.TestCase):
    def test_success_signal_waits_for_sftp_context_and_client_close(self):
        sftp = FakeSftp()
        client = FakeClient(sftp)
        events = []
        job = SftpJob(lambda _connection: client, {}, "list", "/")
        job.signals.finished.connect(lambda value: events.append((value, sftp.closed, client.close_attempted)))

        job.run()

        self.assertEqual(events, [([("sample.txt", False, 7)], True, True)])

    def test_cancel_requested_while_list_blocks_emits_cancelled_after_cleanup(self):
        sftp = FakeSftp()
        client = FakeClient(sftp)
        events = []
        job = SftpJob(lambda _connection: client, {}, "list", "/")
        sftp.before_list = job.cancel
        job.signals.finished.connect(lambda _value: events.append("finished"))
        job.signals.failed.connect(lambda _value: events.append("failed"))
        job.signals.cancelled.connect(lambda: events.append(("cancelled", sftp.closed, client.close_attempted)))

        job.run()

        self.assertEqual(events, [("cancelled", True, True)])

    def test_cancel_before_start_does_not_open_a_client(self):
        calls = []
        events = []
        job = SftpJob(lambda _connection: calls.append("connect"), {}, "list", "/")
        job.cancel()
        job.signals.cancelled.connect(lambda: events.append("cancelled"))
        job.signals.finished.connect(lambda _value: events.append("finished"))
        job.signals.failed.connect(lambda _value: events.append("failed"))

        job.run()

        self.assertEqual(calls, [])
        self.assertEqual(events, ["cancelled"])

    def test_interrupted_error_without_cancel_request_is_failure(self):
        events = []
        def connect(_connection):
            raise InterruptedError("unexpected transport interruption")
        job = SftpJob(connect, {}, "list", "/")
        job.signals.cancelled.connect(lambda: events.append("cancelled"))
        job.signals.failed.connect(lambda message: events.append(message))

        job.run()

        self.assertEqual(len(events), 1)
        self.assertTrue(events[0].startswith("InterruptedError:"))
        self.assertNotIn("cancelled", events)

    def test_failure_signal_waits_for_client_close_attempt(self):
        sftp = FakeSftp(list_error=OSError("offline"))
        client = FakeClient(sftp)
        events = []
        job = SftpJob(lambda _connection: client, {}, "list", "/")
        job.signals.failed.connect(lambda message: events.append((message, sftp.closed, client.close_attempted)))

        job.run()

        self.assertEqual(len(events), 1)
        self.assertTrue(events[0][0].startswith("OSError:"))
        self.assertEqual(events[0][1:], (True, True))


if __name__ == "__main__":
    unittest.main()
