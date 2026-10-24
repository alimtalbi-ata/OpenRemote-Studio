"""Secure SSH tunnel and SFTP helpers. Author: Abdelhalim Talbi."""
import select
import socket
import socketserver
import threading
import math
from numbers import Real
from pathlib import PurePosixPath


def safe_remote_path(base, name):
    if not name or name in ('.', '..') or '/' in name or "\\" in name or "\x00" in name:
        raise ValueError('Nom de fichier distant invalide')
    return str(PurePosixPath(base) / name)


class Tunnel:
    """Loopback-only SSH forwarding with bounded, revocable active channels.

    The SSH client belongs to the caller; this class owns only the local
    listening socket, accepted local sockets and direct-tcpip channels.
    Closing a tunnel actively revokes existing forwarding, not just accepts.
    """

    def __init__(self, client, bind_host, bind_port, target_host, target_port, max_connections=16):
        if bind_host not in ('127.0.0.1', '::1', 'localhost'):
            raise ValueError('Écoute locale uniquement pour éviter une exposition réseau')
        for port in (bind_port, target_port):
            if isinstance(port, bool) or not str(port).isdigit() or not 1 <= int(port) <= 65535:
                raise ValueError('Port invalide')
        if (not isinstance(target_host, str) or not target_host or len(target_host) > 253
                or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in target_host)):
            raise ValueError('Hôte distant invalide')
        if type(max_connections) is not int or not 1 <= max_connections <= 64:
            raise ValueError('Limite de connexions invalide')
        transport = client.get_transport()
        if not transport or not transport.is_active():
            raise RuntimeError('SSH déconnecté')

        self.max_connections = max_connections
        self._lifecycle_lock = threading.Lock()
        self._connections_lock = threading.Lock()
        self._drain_condition = threading.Condition(self._connections_lock)
        self._pending_channel_opens = 0
        # All close() callers must observe completed listener teardown.
        self._close_complete = threading.Event()
        # Accepted local socket -> SSH channel (None until open_channel returns).
        self._connections = {}
        self._started = False
        self._closed = False
        owner = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                local = self.request
                with owner._connections_lock:
                    if owner._closed or len(owner._connections) >= owner.max_connections:
                        return  # Fail closed; socketserver closes the rejected peer.
                    owner._connections[local] = None
                channel = None
                try:
                    if not transport.is_active() or owner._closed:
                        return
                    # Track opens separately from established channels: a blocked
                    # Paramiko open can outlive listener close until its timeout.
                    with owner._drain_condition:
                        if owner._closed:
                            return
                        owner._pending_channel_opens += 1
                    try:
                        channel = transport.open_channel(
                            'direct-tcpip', (target_host, int(target_port)),
                            local.getpeername(), timeout=10)
                    finally:
                        with owner._drain_condition:
                            owner._pending_channel_opens -= 1
                            owner._drain_condition.notify_all()
                    if channel is None:
                        return
                    with owner._connections_lock:
                        if owner._closed:
                            return  # finally closes a late channel.
                        owner._connections[local] = channel
                    while not owner._closed and transport.is_active():
                        ready, _, _ = select.select([local, channel], [], [], 0.25)
                        if local in ready:
                            data = local.recv(32768)
                            if not data:
                                break
                            channel.sendall(data)
                        if channel in ready:
                            data = channel.recv(32768)
                            if not data:
                                break
                            local.sendall(data)
                except Exception:
                    # SSH/socket failures are expected during revocation.
                    # Never leak remote endpoint details or credentials in logs.
                    pass
                finally:
                    # Drain completion means channel.close() has returned,
                    # not merely that the handler was removed from the map.
                    if channel is not None:
                        try:
                            channel.close()
                        except Exception:
                            pass
                    with owner._drain_condition:
                        owner._connections.pop(local, None)
                        owner._drain_condition.notify_all()

        class Server(socketserver.ThreadingTCPServer):
            address_family = socket.AF_INET6 if bind_host == '::1' else socket.AF_INET
            allow_reuse_address = True
            daemon_threads = True
            request_queue_size = 16

        local_host = '127.0.0.1' if bind_host == 'localhost' else bind_host
        self.server = Server((local_host, int(bind_port)), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def active_connections(self):
        """Number of accepted local peers; no addresses or secrets exposed."""
        with self._connections_lock:
            return len(self._connections)

    @property
    def pending_channel_opens(self):
        """Number of SSH channel opens still pending; no endpoint details."""
        with self._connections_lock:
            return self._pending_channel_opens

    def wait_drained(self, timeout=10.0):
        """Wait for accepted handler cleanup after close(); return False on timeout.

        close() revokes active channels and releases the listening port, but
        Paramiko's open_channel() may remain blocked until its own timeout.
        Callers needing a quiescent tunnel can explicitly wait without an
        unbounded hang. This never closes the caller-owned SSH transport.
        """
        if (isinstance(timeout, bool) or not isinstance(timeout, Real)
                or not math.isfinite(timeout) or timeout < 0 or timeout > 120):
            raise ValueError('Délai de drainage invalide')
        with self._drain_condition:
            if not self._closed:
                raise RuntimeError('Fermer le tunnel avant drainage')
            return self._drain_condition.wait_for(
                lambda: not self._connections and self._pending_channel_opens == 0,
                timeout=float(timeout))

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
                try:
                    self.server.server_close()
                finally:
                    self._close_complete.set()
                raise

    def close(self):
        """Revoke forwarding and wait for listener teardown on every call.

        Concurrent callers must not return early while another caller still
        owns the listening port. Pending SSH channel opens can outlive this
        method until their transport timeout; late channels are rejected.
        """
        with self._lifecycle_lock:
            already_closed = self._closed
            if not already_closed:
                self._closed = True
                started = self._started
        if already_closed:
            self._close_complete.wait()
            return
        try:
            # Revoke channels before waiting for the accept loop. The handler
            # may still be opening a channel; it cannot adopt a late result.
            with self._connections_lock:
                connections = tuple(self._connections.items())
            for local, channel in connections:
                if channel is not None:
                    try:
                        channel.close()
                    except Exception:
                        pass
                try:
                    local.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    local.close()
                except OSError:
                    pass
            try:
                if started:
                    self.server.shutdown()
                    if threading.current_thread() is not self.thread:
                        self.thread.join(timeout=3)
            finally:
                self.server.server_close()
        finally:
            # Signal even on teardown failure so no concurrent caller hangs.
            self._close_complete.set()
