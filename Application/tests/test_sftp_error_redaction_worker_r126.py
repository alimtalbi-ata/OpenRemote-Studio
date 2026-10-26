"""R126: prove SftpJob emits safe diagnostics through its Qt failure signal."""
import unittest

try:
    import PySide6  # noqa: F401
except ImportError:
    SftpJob = None
else:
    from PySide6.QtCore import Qt
    from qt_workers import SftpJob


class FailingSftp:
    def __init__(self, error):
        self.error = error
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def listdir_attr(self, _path):
        raise self.error


class FakeSshClient:
    def __init__(self, error):
        self.sftp = FailingSftp(error)
        self.close_count = 0
    def open_sftp(self):
        return self.sftp
    def close(self):
        self.close_count += 1


@unittest.skipIf(SftpJob is None, "PySide6 absent; Windows/cumulative gates must run this integration test")
class SftpErrorRedactionWorkerR126Tests(unittest.TestCase):
    def _run_failure(self, error):
        client = FakeSshClient(error)
        job = SftpJob(lambda _connection: client, {}, "list", "/private")
        messages = []
        job.signals.failed.connect(messages.append, Qt.ConnectionType.DirectConnection)
        job.run()
        self.assertEqual(client.close_count, 1)
        self.assertEqual(len(messages), 1)
        return messages[0]

    def test_worker_does_not_emit_secret_or_path_from_exception(self):
        secret = "R126_WORKER_SECRET_MUST_NOT_ESCAPE"
        message = self._run_failure(RuntimeError(
            f"password={secret}; local=/private/customer/key.pem"))
        self.assertEqual(message, "Échec de l’opération SFTP. Détails techniques masqués.")
        self.assertNotIn(secret, message)
        self.assertNotIn("/private/customer", message)
        self.assertNotIn("password=", message)

    def test_worker_preserves_safe_error_category_without_remote_path(self):
        message = self._run_failure(FileNotFoundError(
            2, "private-detail", "/srv/customer/private.key"))
        self.assertEqual(message, "Fichier ou chemin SSH/SFTP introuvable.")
        self.assertNotIn("/srv/customer", message)


if __name__ == "__main__":
    unittest.main()
