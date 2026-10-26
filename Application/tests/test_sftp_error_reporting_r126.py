"""R126: fixed SFTP diagnostic taxonomy must not expose exception payloads."""
import errno
import unittest
from sftp_error_reporting import safe_sftp_error_message


class SftpErrorReportingR126Tests(unittest.TestCase):
    def test_generic_exception_secret_and_private_path_are_not_returned(self):
        marker = "R126_SECRET_DO_NOT_LOG"
        message = safe_sftp_error_message(RuntimeError(
            f"password={marker}; private=/srv/customer/backup.key"))
        self.assertEqual(message, "Échec de l’opération SFTP. Détails techniques masqués.")
        self.assertNotIn(marker, message)
        self.assertNotIn("/srv/customer", message)
        self.assertNotIn("password=", message)

    def test_never_calls_exception_stringification(self):
        class UnprintableError(RuntimeError):
            def __str__(self):
                raise AssertionError("str(exc) must not be called")
            def __repr__(self):
                raise AssertionError("repr(exc) must not be called")
        self.assertEqual(safe_sftp_error_message(UnprintableError()),
                         "Échec de l’opération SFTP. Détails techniques masqués.")

    def test_timeout_has_stable_message(self):
        self.assertEqual(safe_sftp_error_message(TimeoutError("credential=secret")),
                         "Le délai de l’opération SSH/SFTP a expiré.")

    def test_permission_error_does_not_echo_remote_name(self):
        self.assertEqual(safe_sftp_error_message(PermissionError(errno.EACCES, "private-target")),
                         "Accès SSH/SFTP refusé.")

    def test_missing_file_does_not_echo_remote_path(self):
        self.assertEqual(safe_sftp_error_message(FileNotFoundError(
            errno.ENOENT, "missing", "/sensitive/team/backup")),
            "Fichier ou chemin SSH/SFTP introuvable.")

    def test_connection_reset_is_classified_without_details(self):
        self.assertEqual(safe_sftp_error_message(ConnectionResetError(
            errno.ECONNRESET, "token=secret")),
            "La connexion SSH/SFTP a été interrompue.")

    def test_errno_property_failure_falls_back_without_stringifying(self):
        class HostileError(Exception):
            @property
            def errno(self):
                raise RuntimeError("do-not-surface-this")
            def __str__(self):
                raise AssertionError("str(exc) must not be called")
        self.assertEqual(safe_sftp_error_message(HostileError()),
                         "Échec de l’opération SFTP. Détails techniques masqués.")


if __name__ == "__main__":
    unittest.main()
