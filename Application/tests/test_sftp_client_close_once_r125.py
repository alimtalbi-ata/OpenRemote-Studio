"""R125: make Paramiko client shutdown single-flight and retry failures.

The tests use a blocked SFTP request and an injected client. They prove the
worker's terminal signal follows completed cleanup and that concurrent
cancellation/finalization does not invoke close concurrently.
"""
import threading
import unittest
from types import SimpleNamespace

try:
    import PySide6  # noqa: F401
except ImportError:
    SftpJob = None
else:
    from PySide6.QtCore import Qt
    from qt_workers import SftpJob


class BlockingSftp:
    def __init__(self, *, fail=False):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.closed = False
        self.fail = fail

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True
        return False

    def listdir_attr(self, _path):
        self.entered.set()
        if not self.release.wait(5):
            raise TimeoutError("fixture timed out waiting for client close")
        if self.fail:
            raise OSError("synthetic transport failure")
        return [SimpleNamespace(filename="safe.txt", st_mode=0, st_size=4)]


class FakeClient:
    def __init__(self, sftp, *, block_first_close=False, fail_first_close=False):
        self.sftp = sftp
        self.close_started = threading.Event()
        self.allow_close_return = threading.Event()
        self.close_count = 0
        self.block_first_close = block_first_close
        self.fail_first_close = fail_first_close
        self._count_lock = threading.Lock()

    def open_sftp(self):
        return self.sftp

    def close(self):
        with self._count_lock:
            self.close_count += 1
            call = self.close_count
        self.close_started.set()
        # Closing the transport is what releases the intentionally blocked
        # request. The separate event holds close() open to create a race.
        self.sftp.release.set()
        if self.block_first_close and call == 1:
            if not self.allow_close_return.wait(5):
                raise TimeoutError("fixture timed out waiting to finish close")
        if self.fail_first_close and call == 1:
            raise OSError("synthetic close failure")


@unittest.skipIf(SftpJob is None, "PySide6 unavailable; native/cumulative CI must run R125")
class SftpClientCloseOnceR125Tests(unittest.TestCase):
    def test_successful_job_closes_client_exactly_once(self):
        sftp = BlockingSftp()
        sftp.release.set()
        client = FakeClient(sftp)
        outcomes = []
        job = SftpJob(lambda _connection: client, {}, "list", "/")
        job.signals.finished.connect(lambda value: outcomes.append(("finished", value)))
        job.signals.failed.connect(lambda message: outcomes.append(("failed", message)))

        job.run()

        self.assertEqual(client.close_count, 1)
        self.assertTrue(sftp.closed)
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0][0], "finished")

    def test_concurrent_cancel_and_finalizer_do_not_close_client_twice(self):
        sftp = BlockingSftp()
        client = FakeClient(sftp, block_first_close=True)
        outcomes = []
        job = SftpJob(lambda _connection: client, {}, "list", "/")
        # The worker runs on a Python thread in this deterministic race test.
        # Force direct delivery so assertions do not depend on a Qt event loop.
        direct = Qt.ConnectionType.DirectConnection
        job.signals.cancelled.connect(lambda: outcomes.append(("cancelled", sftp.closed)), direct)
        job.signals.finished.connect(lambda _value: outcomes.append(("finished",)), direct)
        job.signals.failed.connect(lambda _value: outcomes.append(("failed",)), direct)

        worker = threading.Thread(target=job.run, daemon=True)
        worker.start()
        self.assertTrue(sftp.entered.wait(2), "worker never entered the SFTP request")

        first_cancel = threading.Thread(target=job.cancel, daemon=True)
        first_cancel.start()
        self.assertTrue(client.close_started.wait(2), "cancel did not start client close")
        second_cancel = threading.Thread(target=job.cancel, daemon=True)
        second_cancel.start()

        # The SFTP request is released, but worker finalization must wait for
        # the in-flight close instead of racing a second Paramiko close call.
        self.assertTrue(worker.is_alive())
        self.assertEqual(client.close_count, 1)
        client.allow_close_return.set()

        for thread in (first_cancel, second_cancel, worker):
            thread.join(3)
            self.assertFalse(thread.is_alive(), "close race did not drain")
        self.assertEqual(client.close_count, 1)
        self.assertEqual(outcomes, [("cancelled", True)])

    def test_failed_cancel_close_is_retried_by_final_cleanup(self):
        sftp = BlockingSftp(fail=True)
        client = FakeClient(sftp, fail_first_close=True)
        outcomes = []
        job = SftpJob(lambda _connection: client, {}, "list", "/")
        direct = Qt.ConnectionType.DirectConnection
        job.signals.cancelled.connect(lambda: outcomes.append(("cancelled", sftp.closed, client.close_count)), direct)
        job.signals.failed.connect(lambda _value: outcomes.append(("failed",)), direct)
        job.signals.finished.connect(lambda _value: outcomes.append(("finished",)), direct)

        worker = threading.Thread(target=job.run, daemon=True)
        worker.start()
        self.assertTrue(sftp.entered.wait(2), "worker never entered the SFTP request")
        cancel = threading.Thread(target=job.cancel, daemon=True)
        cancel.start()
        cancel.join(2)
        worker.join(3)

        self.assertFalse(cancel.is_alive())
        self.assertFalse(worker.is_alive())
        self.assertEqual(client.close_count, 2, "failed close should be retried once by final cleanup")
        self.assertEqual(outcomes, [("cancelled", True, 2)])

    def test_unsolicited_transport_failure_closes_once_before_failure_signal(self):
        sftp = BlockingSftp(fail=True)
        sftp.release.set()
        client = FakeClient(sftp)
        outcomes = []
        job = SftpJob(lambda _connection: client, {}, "list", "/")
        job.signals.failed.connect(lambda message: outcomes.append((message, sftp.closed, client.close_count)))

        job.run()

        self.assertEqual(client.close_count, 1)
        self.assertEqual(len(outcomes), 1)
        self.assertTrue(outcomes[0][0].startswith("OSError:"))
        self.assertEqual(outcomes[0][1:], (True, 1))


if __name__ == "__main__":
    unittest.main()
