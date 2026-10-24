"""R82: opt-in SSH forwarding lifecycle independent of Qt.
No network is attempted until start(). The scope owns the SSH client and tunnel.
Author: Abdelhalim Talbi.
"""
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock, Thread
import unicodedata

from network_resource_scope import NetworkResourceScope
from remote_tools import Tunnel
from ssh_transport import SSHSettings, create_ssh_client
from tunnel_shutdown_status import TunnelShutdownStatus


@dataclass(frozen=True)
class TunnelSnapshot:
    phase: str
    active_connections: int = 0
    pending_channel_opens: int = 0


def _port(value):
    if type(value) is not int or not 1 <= value <= 65535:
        raise ValueError('invalid tunnel port')
    return value


def _target(value):
    if (not isinstance(value, str) or not value or len(value) > 253
            or value != value.strip()
            or any(c.isspace() or unicodedata.category(c) in ('Cc', 'Cf') for c in value)):
        raise ValueError('invalid tunnel destination')
    return value


class TunnelController:
    """One-shot local-only forwarding; stop is idempotent and nonblocking.

    Failures are classified without exception text, which can contain
    hostnames, usernames or private-key paths. No auto-reconnect.
    """
    def __init__(self, connector=create_ssh_client, tunnel_factory=Tunnel):
        self._connector = connector
        self._tunnel_factory = tunnel_factory
        self._lock = Lock()
        self._scope = NetworkResourceScope()
        self._startup_done = Event()
        self._startup_done.set()
        self._state = 'idle'
        self._tunnel = None
        self._client = None
        self._worker = None
        self._watchdog = None
        self._watchdog_stop = Event()

    def start(self, settings, *, key_filename, local_port, target_host, target_port):
        if not isinstance(settings, SSHSettings):
            raise ValueError('SSH settings required')
        settings.validate()
        _port(local_port)
        _port(target_port)
        _target(target_host)
        if not isinstance(key_filename, str) or not key_filename or not Path(key_filename).is_file():
            raise ValueError('SSH private key file required')
        with self._lock:
            if self._state != 'idle':
                raise RuntimeError('tunnel controller already used')
            self._state = 'connecting'
            self._startup_done.clear()

        def run():
            try:
                if self._scope.cancelled:
                    return
                client = self._connector(settings, key_filename=key_filename)
                if not self._scope.register(client):
                    return
                with self._lock:
                    self._client = client
                if self._scope.cancelled:
                    return
                tunnel = self._tunnel_factory(client, '127.0.0.1', local_port,
                                              target_host, target_port)
                if not self._scope.register(tunnel):
                    return
                with self._lock:
                    self._tunnel = tunnel
                if self._scope.cancelled:
                    return
                tunnel.start()
                # A concurrent stop may have set 'closing' before scope.cancelled.
                # Never resurrect a tunnel after revocation was requested.
                with self._lock:
                    if self._state == 'connecting' and not self._scope.cancelled:
                        self._state = 'active'
                        watchdog = Thread(target=self._watch_link,
                                          name='ssh-tunnel-health', daemon=True)
                        self._watchdog = watchdog
                    else:
                        watchdog = None
                if watchdog is not None:
                    watchdog.start()
            except Exception:
                self._watchdog_stop.set()
                with self._lock:
                    if not self._scope.cancelled:
                        self._state = 'failed'
                self._scope.close()
            finally:
                self._startup_done.set()

        self._worker = Thread(target=run, name='ssh-tunnel-startup', daemon=True)
        self._worker.start()

    def _check_link_health(self):
        """Fail closed on SSH loss without a Qt event-loop dependency."""
        with self._lock:
            if self._state != 'active' or self._scope.cancelled:
                return
            client = self._client
        try:
            transport = client.get_transport() if client is not None else None
            alive = transport is not None and transport.is_active()
        except Exception:
            alive = False
        if alive:
            return
        with self._lock:
            if self._state != 'active' or self._scope.cancelled:
                return
            self._state = 'disconnected'
        self._watchdog_stop.set()
        self._scope.close()

    def _watch_link(self):
        # Event.wait() makes shutdown immediate without a busy loop or GUI I/O.
        # Paramiko transport.is_active() is a local state check, not a probe.
        while not self._watchdog_stop.wait(0.2):
            self._check_link_health()
            with self._lock:
                if self._state != 'active':
                    return

    def stop(self):
        """Request revocation without waiting for network or listener I/O."""
        self._watchdog_stop.set()
        with self._lock:
            if self._state == 'idle':
                self._state = 'closed'
            elif self._state not in ('closed', 'failed', 'disconnected'):
                self._state = 'closing'
        self._scope.close()

    close = stop

    def poll(self):
        """Read a sanitized, nonblocking snapshot for Qt's event loop.

        Also checks SSH health immediately; a background watchdog performs
        the same fail-closed revocation even when Qt does not poll. No network
        call, credentials or endpoint is exposed.
        """
        self._check_link_health()
        with self._lock:
            state, tunnel = self._state, self._tunnel
        if state == 'idle':
            return TunnelSnapshot('idle')
        if not self._startup_done.is_set():
            return TunnelSnapshot('closing' if self._scope.cancelled else 'connecting')
        if self._scope.closed:
            phase = TunnelShutdownStatus(self._scope, tunnel).poll()
            if phase != 'complete':
                return TunnelSnapshot(phase)
            return TunnelSnapshot(state if state in ('failed', 'disconnected') else 'closed')
        if state == 'active' and tunnel is not None:
            return TunnelSnapshot('active', tunnel.active_connections,
                                  tunnel.pending_channel_opens)
        return TunnelSnapshot(state)

    def is_shutdown_complete(self):
        return self.poll().phase in ('idle', 'closed', 'failed', 'disconnected')
