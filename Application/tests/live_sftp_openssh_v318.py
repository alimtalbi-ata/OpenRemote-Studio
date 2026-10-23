"""Live SFTP smoke test against an OpenSSH container. Author: Abdelhalim Talbi."""
import os
import hashlib
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
        # R71: use a REAL OpenSSH transport while replacing the local
        # resume lock during the transfer. The previous target must survive.
        conflict_target = root / 'lock-swap-r71.bin'
        conflict_target.write_bytes(b'EXISTING LOCAL CONTENT')
        token = hashlib.sha256(('ci-lock-r71\0' + remote + '\0' +
                                str(conflict_target.resolve())).encode()).hexdigest()[:20]
        lock = root / ('.openremote-' + token + '.lock')
        partial = root / ('.openremote-' + token + '.part')
        replaced = {'done': False}
        def replace_lock_on_progress(done, total):
            if done > 0 and not replaced['done']:
                lock.unlink()
                lock.write_text('replacement-owner')
                replaced['done'] = True
        try:
            try:
                download_resume_verified(sftp, remote, conflict_target, 'ci-lock-r71',
                                         callback=replace_lock_on_progress, chunk_size=1024)
            except RuntimeError as exc:
                assert 'Verrou' in str(exc), str(exc)
            else:
                raise AssertionError('R71 published after lock ownership was lost')
            assert replaced['done'], 'R71 lock swap callback did not execute'
            assert conflict_target.read_bytes() == b'EXISTING LOCAL CONTENT'
            assert lock.read_text() == 'replacement-owner'
            assert partial.exists(), 'R71 should retain staged bytes for diagnosis'
        finally:
            lock.unlink(missing_ok=True)
            partial.unlink(missing_ok=True)
        try:
            upload_exclusive(sftp, source, remote)
        except (OSError, IOError):
            pass
        else:
            raise AssertionError('Exclusive upload overwrote existing remote file')
        sftp.remove(remote)
        print('LIVE_SFTP_PASS: upload exclusive, atomic download, verified resume, overwrite rejection, R71 lock ownership')
finally:
    client.close()
