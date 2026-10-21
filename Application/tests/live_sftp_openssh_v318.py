"""Live SFTP smoke test against an OpenSSH container. Author: Abdelhalim Talbi."""
import os
import tempfile
from pathlib import Path
import paramiko
from transfer_safety import download_atomic, download_resume_verified, upload_exclusive

host = os.environ.get('SFTP_TEST_HOST', '127.0.0.1')
port = int(os.environ.get('SFTP_TEST_PORT', '2222'))
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Ephemeral CI fixture only; never production.
try:
    client.connect(host, port=port, username='tester', password='testpassword', timeout=10,
                   auth_timeout=10, banner_timeout=10)
    with client.open_sftp() as sftp, tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        source = root / 'source.bin'
        source.write_bytes(bytes(range(256)) * 64)
        remote = '/upload/openremote-live.bin'
        upload_exclusive(sftp, source, remote)
        assert sftp.stat(remote).st_size == source.stat().st_size
        target = root / 'atomic.bin'
        download_atomic(sftp, remote, target)
        assert target.read_bytes() == source.read_bytes()
        resumed = root / 'resumed.bin'
        result = download_resume_verified(sftp, remote, resumed, 'ci-openssh', chunk_size=1024)
        assert result == source.stat().st_size
        assert resumed.read_bytes() == source.read_bytes()
        try:
            upload_exclusive(sftp, source, remote)
        except (OSError, IOError):
            pass
        else:
            raise AssertionError('Exclusive upload overwrote existing remote file')
        sftp.remove(remote)
        print('LIVE_SFTP_PASS: upload exclusive, atomic download, verified resume, overwrite rejection')
finally:
    client.close()
