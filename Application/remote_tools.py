"""Secure SSH tunnel and SFTP helpers. Author: Abdelhalim Talbi."""
import select
import socket
import socketserver
import threading
from pathlib import PurePosixPath


def safe_remote_path(base, name):
    if not name or name in ('.', '..') or '/' in name or "\\" in name or "\x00" in name:
        raise ValueError('Nom de fichier distant invalide')
    return str(PurePosixPath(base) / name)


class Tunnel:
    """Loopback-only SSH forwarding with race-safe, idempotent shutdown.

    Constructing the tunnel reserves its listening socket; a cancelled worker
    may therefore close it *before* start(). Never call socketserver.shutdown()
    in that state: it waits indefinitely for serve_forever() to begin.
    """

    def __init__(self, client, bind_host, bind_port, target_host, target_port):
        if bind_host not in ('127.0.0.1', '::1', 'localhost'):
            raise ValueError('Écoute locale uniquement pour éviter une exposition réseau')
        for port in (bind_port, target_port):
            if isinstance(port, bool) or not str(port).isdigit() or not 1 <= int(port) <= 65535:
                raise ValueError('Port invalide')
        if (not isinstance(target_host, str) or not target_host or len(target_host) > 253
                or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in target_host)):
            raise ValueError('Hôte distant invalide')
        transport = client.get_transport()
        if not transport or not transport.is_active():
            raise RuntimeError('SSH déconnecté')

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                channel = transport.open_channel(
                    'direct-tcpip', (target_host, int(target_port)), self.request.getpeername())
                if channel is None:
                    return
                try:
                    while True:
                        ready, _, _ = select.select([self.request, channel], [], [], 1)
                        if self.request in ready:
                            data = self.request.recv(32768)
                            if not data:
                                break
                            channel.sendall(data)
                        if channel in ready:
                            data = channel.recv(32768)
                            if not data:
                                break
                            self.request.sendall(data)
                except (OSError, EOFError):
                    pass  # Peer closed; do not expose network exception contents.
                finally:
                    channel.close()

        class Server(socketserver.ThreadingTCPServer):
            address_family = socket.AF_INET6 if bind_host == '::1' else socket.AF_INET
            allow_reuse_address = True
            daemon_threads = True

        # 'localhost' is explicitly IPv4 loopback, not a resolver-dependent bind.
        local_host = '127.0.0.1' if bind_host == 'localhost' else bind_host
        self.server = Server((local_host, int(bind_port)), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._lifecycle_lock = threading.Lock()
        self._started = False
        self._closed = False

    def start(self):
        with self._lifecycle_lock:
            if self._closed:
                raise RuntimeError('Tunnel déjà fermé')
            if self._started:
                raise RuntimeError('Tunnel déjà démarré')
            try:
                self.thread.start()
                self._started = True
            except BaseException:
                self._closed = True
                self.server.server_close()
                raise

    def close(self):
        with self._lifecycle_lock:
            if self._closed:
                return
            self._closed = True
            started = self._started
        try:
            if started:
                self.server.shutdown()
                if threading.current_thread() is not self.thread:
                    self.thread.join(timeout=3)
        finally:
            self.server.server_close()
