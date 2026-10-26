"""R127: safe TCP error taxonomy and network_probe integration."""
import errno
import socket
import unittest

from network_error_reporting import safe_tcp_error_message
from network_probe import probe


class NetworkErrorReportingR127Tests(unittest.TestCase):
    def test_refused_connection_does_not_echo_exception_payload(self):
        marker = "R127_PASSWORD_DO_NOT_EXPORT"
        error = ConnectionRefusedError(
            errno.ECONNREFUSED, f"password={marker}; path=/private/customer/endpoint"
        )
        message = safe_tcp_error_message(error)
        self.assertEqual(
            message,
            "Connexion refusée par la cible (port fermé ou service arrêté).",
        )
        self.assertNotIn(marker, message)
        self.assertNotIn("/private/customer", message)
        self.assertNotIn("ConnectionRefusedError", message)

    def test_timeout_is_actionable_but_fixed(self):
        marker = "R127_TIMEOUT_SECRET"
        self.assertEqual(
            safe_tcp_error_message(TimeoutError(f"token={marker}")),
            "Délai de connexion dépassé.",
        )

    def test_dns_failure_is_classified_without_echoing_hostname(self):
        marker = "R127_PRIVATE_DNS_VALUE"
        code = getattr(socket, "EAI_NONAME", -2)
        message = safe_tcp_error_message(socket.gaierror(code, marker))
        self.assertEqual(message, "Résolution du nom impossible.")
        self.assertNotIn(marker, message)

    def test_permission_failure_is_fixed(self):
        self.assertEqual(
            safe_tcp_error_message(PermissionError(errno.EACCES, "private endpoint")),
            "Connexion refusée par la politique locale.",
        )

    def test_hostile_exception_is_never_stringified(self):
        class HostileError(Exception):
            @property
            def errno(self):
                raise RuntimeError("R127_PRIVATE_ERRNO")

            def __str__(self):
                raise AssertionError("str(exc) must not be called")

            def __repr__(self):
                raise AssertionError("repr(exc) must not be called")

        self.assertEqual(
            safe_tcp_error_message(HostileError()),
            "Erreur réseau non détaillée (détails masqués).",
        )

    def test_probe_uses_safe_taxonomy_and_never_echoes_raw_error(self):
        marker = "R127_CONNECTOR_SECRET"

        def fail(_address, timeout):
            self.assertEqual(timeout, 2.0)
            raise OSError(errno.ECONNREFUSED, f"credential={marker}; /private/customer")

        result = probe(
            {"protocol": "SSH", "host": "server.example", "port": 22},
            connector=fail,
        )
        self.assertFalse(result["reachable"])
        self.assertIn("Connexion refusée", result["message"])
        self.assertNotIn(marker, result["message"])
        self.assertNotIn("/private/customer", result["message"])
        self.assertNotIn("OSError", result["message"])


if __name__ == "__main__":
    unittest.main()
