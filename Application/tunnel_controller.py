"""R82: opt-in SSH forwarding lifecycle independent of Qt.
No network is attempted until start(). The scope owns the SSH client and tunnel.
Author: Abdelhalim Talbi.
"""
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic
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
    failure_code: str = 'none'


def _safe_ssh_failure_code(error):
    """Classify Paramiko errors by type, never by their potentially sensitive text.

    The result is a fixed, non-sensitive vocabulary suitable for UI display.
    """
    try:
        from paramiko.ssh_exception import BadHostKeyException, AuthenticationException
    except ImportError:
        return 'generic'
    if isinstance(error, BadHostKeyException):
        return 'host_key'
    if isinstance(error, AuthenticationException):
        return 'authentication'
    return 'generic'


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
        self._failure_code = 'none'
        self._tunnel = None
        self._client = None
        self._worker = None
        self._watchdog = None
        self._watchdog_stop = Event()
        self._probe_interval_seconds = 0
        self._probe_timeout_seconds = 5

    def start(self, settings, *, key_filename, local_port, target_host, target_port,
              keepalive_seconds=0, probe_interval_seconds=0, probe_timeout_seconds=5):
        if not isinstance(settings, SSHSettings):
            raise ValueError('SSH settings required')
        settings.validate()
        if type(keepalive_seconds) is not int or not 0 <= keepalive_seconds <= 300:
            raise ValueError('invalid SSH keepalive interval')
        if type(probe_interval_seconds) is not int or not 0 <= probe_interval_seconds <= 300:
            raise ValueError('invalid SSH probe interval')
        if type(probe_timeout_seconds) is not int or not 1 <= probe_timeout_seconds <= 30:
            raise ValueError('invalid SSH probe timeout')
        _port(local_port)
        _port(target_port)
        _target(target_host)
        if not isinstance(key_filename, str) or not key_filename or not Path(key_filename).is_file():
            raise ValueError('SSH private key file required')
        with self._lock:
            if self._state != 'idle':
                raise RuntimeError('tunnel controller already used')
            self._state = 'connecting'
            self._probe_interval_seconds = probe_interval_seconds
            self._probe_timeout_seconds = probe_timeout_seconds
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
                if keepalive_seconds:
                    # Configure before binding a local listener; fail closed on unsupported transports.
                    transport = client.get_transport()
                    if transport is None or not transport.is_active():
                        raise RuntimeError('SSH transport unavailable')
                    transport.set_keepalive(keepalive_seconds)
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
            except Exception as error:
                failure_code = _safe_ssh_failure_code(error)
                self._watchdog_stop.set()
                with self._lock:
                    if not self._scope.cancelled:
                        self._state = 'failed'
                        self._failure_code = failure_code
                self._scope.close()
            finally:
                self._startup_done.set()

        self._worker = Thread(target=run, name='ssh-tunnel-startup', daemon=True)
        self._worker.start()

    def _disconnect(self):
        """Revoke exactly once; no network operation or secret-bearing status."""
        with self._lock:
            if self._state != 'active' or self._scope.cancelled:
                return
            self._state = 'disconnected'
        self._watchdog_stop.set()
        self._scope.close()

    def _check_link_health(self):
        """Fail closed on local SSH transport loss without Qt polling."""
        with self._lock:
            if self._state != 'active' or self._scope.cancelled:
                return
            client = self._client
        try:
            transport = client.get_transport() if client is not None else None
            alive = transport is not None and transport.is_active()
        except Exception:
            alive = False
        if not alive:
            self._disconnect()

    def _watch_link(self):
        """Watch local transport and optionally require bounded SSH replies.

        Paramiko keepalive sends packets but does not demand replies. When the
        operator opts in, an SSH global request requires a server response.
        OpenSSH can reject the unknown request: the rejection *is* a response.
        The request runs on at most one daemon worker because a blackholed
        transport may block indefinitely; the watchdog never waits on it.
        """
        interval = self._probe_interval_seconds
        timeout = self._probe_timeout_seconds
        next_probe = monotonic() + interval if interval else None
        probe_done = None
        probe_result = None
        deadline = None
        while not self._watchdog_stop.wait(0.2):
            self._check_link_health()
            with self._lock:
                if self._state != 'active':
                    return
                client = self._client
            if not interval:
                continue
            now = monotonic()
            if probe_done is not None:
                if probe_done.is_set():
                    if not probe_result[0]:
                        self._disconnect()
                        return
                    probe_done = None
                    probe_result = None
                    next_probe = now + interval
                elif now >= deadline:
                    self._disconnect()
                    return
            elif now >= next_probe:
                probe_done = Event()
                probe_result = [False]
                try:
                    transport = client.get_transport()
                    if transport is None or not transport.is_active():
                        self._disconnect()
                        return
                except Exception:
                    self._disconnect()
                    return

                def request_reply(transport=transport, done=probe_done, result=probe_result):
                    try:
                        # None is the expected SSH_MSG_REQUEST_FAILURE from OpenSSH.
                        # It still proves that a reply arrived if transport is alive.
                        transport.global_request('keepalive@openssh.com', wait=True)
                        result[0] = bool(transport.is_active())
                    except Exception:
                        result[0] = False
                    finally:
                        done.set()

                Thread(target=request_reply, name='ssh-tunnel-probe', daemon=True).start()
                deadline = monotonic() + timeout

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
            return TunnelSnapshot(state if state in ('failed', 'disconnected') else 'closed',
                                  failure_code=self._failure_code if state == 'failed' else 'none')
        if state == 'active' and tunnel is not None:
            return TunnelSnapshot('active', tunnel.active_connections,
                                  tunnel.pending_channel_opens)
        return TunnelSnapshot(state)

    def is_shutdown_complete(self):
        return self.poll().phase in ('idle', 'closed', 'failed', 'disconnected')
