"""R124: cancel a blocked SFTP worker by closing its active SSH client.

The fake SFTP request is deliberately held until the client is closed. This
proves the worker has an interruption path without killing a Python thread.
Windows/OpenSSH CI supplies PySide6; Qt-free lanes skip this integration test.
"""
import threading
import unittest
from types import SimpleNamespace

try:
    import PySide6  # noqa: F401
except ImportError:
    SftpJob = None
else:
    from qt_workers import SftpJob


class BlockingSftp:
    def __init__(self, *, fail_after_release=False):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.closed = False
        self.fail_after_release = fail_after_release

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True
        return False

    def listdir_attr(self, _path):
        self.entered.set()
        if not self.release.wait(3):
            raise TimeoutError("test fixture release timeout")
        if self.fail_after_release:
            raise OSError("simulated socket close")
        return [SimpleNamespace(filename="sample.txt", st_mode=0, st_size=7)]


class FakeClient:
    def __init__(self, sftp, *, raise_on_close=False):
        self.sftp = sftp
        self.close_attempted = threading.Event()
        self.close_count = 0
        self.raise_on_close = raise_on_close
        self.open_sftp_calls = 0
        self._lock = threading.Lock()

    def open_sftp(self):
        self.open_sftp_calls += 1
        return self.sftp

    def close(self):
        with self._lock:
            self.close_count += 1
        self.close_attempted.set()
        self.sftp.release.set()
        if self.raise_on_close:
            raise OSError("simulated close error")


@unittest.skipIf(SftpJob is None, "PySide6 unavailable; native CI must execute R124")
class SftpCancelInterruptR124Tests(unittest.TestCase):
    def _cancel_while_blocked(self, *, fail_after_release=False, raise_on_close=False):
        sftp = BlockingSftp(fail_after_release=fail_after_release)
        client = FakeClient(sftp, raise_on_close=raise_on_close)
        outcomes = []
        job = SftpJob(lambda _connection: client, {}, "list", "/")

        job.signals.finished.connect(lambda value: outcomes.append(("finished", value)))
        job.signals.failed.connect(lambda message: outcomes.append(("failed", message)))
        job.signals.cancelled.connect(
            lambda: outcomes.append(("cancelled", sftp.closed, client.close_attempted.is_set()))
        )

        def cancel_when_request_is_in_flight():
            if sftp.entered.wait(2):
                job.cancel()

        canceller = threading.Thread(target=cancel_when_request_is_in_flight, daemon=True)
        canceller.start()
        job.run()
        canceller.join(2)

        self.assertFalse(canceller.is_alive(), "cancel thread did not finish")
        self.assertTrue(client.close_attempted.is_set(), "cancel did not close the active client")
        self.assertTrue(sftp.closed, "SFTP context was not closed before terminal notification")
        self.assertEqual(len(outcomes), 1, "worker must emit one terminal result")
        self.assertEqual(outcomes[0][0], "cancelled", outcomes)
        self.assertEqual(outcomes[0][1:], (True, True))
        return client, sftp, outcomes

    def test_cancel_closes_active_client_and_releases_blocked_list(self):
        self._cancel_while_blocked()

    def test_transport_error_caused_by_cancel_is_cancelled_not_failed(self):
        self._cancel_while_blocked(fail_after_release=True, raise_on_close=True)

    def test_unsolicited_transport_error_remains_failure(self):
        sftp = BlockingSftp(fail_after_release=True)
        sftp.release.set()
        client = FakeClient(sftp)
        outcomes = []
        job = SftpJob(lambda _connection: client, {}, "list", "/")
        job.signals.finished.connect(lambda value: outcomes.append(("finished", value)))
        job.signals.failed.connect(lambda message: outcomes.append(("failed", message)))
        job.signals.cancelled.connect(lambda: outcomes.append(("cancelled",)))

        job.run()

        self.assertTrue(sftp.closed)
        self.assertTrue(client.close_attempted.is_set())
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0][0], "failed")
        # R126 intentionally removes third-party exception text from the UI signal.
        self.assertEqual(
            outcomes[0][1],
            "Échec de l’opération SFTP. Détails techniques masqués.",
        )
        self.assertNotIn("simulated socket close", outcomes[0][1])

    def test_cancel_during_connect_does_not_open_sftp_channel(self):
        sftp = BlockingSftp()
        client = FakeClient(sftp)
        outcomes = []
        holder = {}

        def connect(_connection):
            holder["job"].cancel()
            return client

        job = SftpJob(connect, {}, "list", "/")
        holder["job"] = job
        job.signals.finished.connect(lambda value: outcomes.append(("finished", value)))
        job.signals.failed.connect(lambda message: outcomes.append(("failed", message)))
        job.signals.cancelled.connect(lambda: outcomes.append(("cancelled",)))

        job.run()

        self.assertEqual(client.open_sftp_calls, 0)
        self.assertTrue(client.close_attempted.is_set())
        self.assertEqual(outcomes, [("cancelled",)])


if __name__ == "__main__":
    unittest.main()
