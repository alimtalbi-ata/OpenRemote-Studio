"""R127: prove the actual Qt TcpJob signal contains no raw exception payload."""
import errno
import unittest
from unittest.mock import patch

try:
    from PySide6.QtCore import Qt
    from qt_workers import TcpJob
except ImportError:
    Qt = None
    TcpJob = None


@unittest.skipIf(
    TcpJob is None,
    "PySide6 absent; Windows and cumulative gates must run this integration test",
)
class TcpErrorRedactionWorkerR127Tests(unittest.TestCase):
    def _run_job(self, host, port, side_effect=None, return_value=None):
        messages = []
        job = TcpJob(host, port)
        job.signals.finished.connect(messages.append, Qt.ConnectionType.DirectConnection)
        with patch(
            "socket.create_connection",
            side_effect=side_effect,
            return_value=return_value,
        ) as connector:
            job.run()
        self.assertEqual(len(messages), 1)
        return messages[0], connector

    def test_raw_os_error_payload_never_reaches_qt_signal(self):
        marker = "R127_WORKER_SECRET_MUST_NOT_ESCAPE"
        error = ConnectionRefusedError(
            errno.ECONNREFUSED, f"password={marker}; path=/private/customer/key"
        )
        message, connector = self._run_job("server.example", 22, side_effect=error)
        connector.assert_called_once_with(("server.example", 22), timeout=2)
        self.assertIn("Connexion refusée", message)
        self.assertNotIn(marker, message)
        self.assertNotIn("/private/customer", message)
        self.assertNotIn("password=", message)
        self.assertNotIn("ConnectionRefusedError", message)

    def test_invalid_host_is_masked_and_no_socket_is_opened(self):
        marker = "R127_HOST_CREDENTIAL"
        message, connector = self._run_job(f"operator:{marker}@server.example", 22)
        connector.assert_not_called()
        self.assertEqual(
            message,
            "TCP [cible masquée] — Indisponible : hôte ou port invalide.",
        )
        self.assertNotIn(marker, message)
        self.assertNotIn("operator@", message)

    def test_ipv6_target_is_bracketed_for_unambiguous_display(self):
        class DummySocket:
            def __enter__(self):
                return self

            def __exit__(self, _kind, _value, _traceback):
                return False

        message, connector = self._run_job(
            "2001:db8::1", 2222, return_value=DummySocket()
        )
        connector.assert_called_once_with(("2001:db8::1", 2222), timeout=2)
        self.assertEqual(message, "TCP [2001:db8::1]:2222 — Accessible")

    def test_timeout_uses_fixed_message(self):
        marker = "R127_TIMEOUT_SECRET"
        message, _connector = self._run_job(
            "server.example", 22, side_effect=TimeoutError(f"token={marker}")
        )
        self.assertIn("Délai de connexion dépassé.", message)
        self.assertNotIn(marker, message)


if __name__ == "__main__":
    unittest.main()
