"""PTY-backed SSH shell transport; no terminal emulation. Author: Abdelhalim Talbi."""
import queue
import threading
import codecs
import time
from PySide6.QtCore import QThread, Signal
from ssh_session_state import classify_failure
from ssh_hop_diagnostics import hop_status
from gateways import validate_route, host as valid_host
from ssh_route_client import RoutedSshClient


def validate_pty_target(connection, route):
    if connection.get('protocol') not in ('SSH','SFTP'):
        raise ValueError('PTY disponible uniquement pour SSH/SFTP')
    checked=validate_route(route)
    if checked['mode'] not in ('','direct','ssh_jump'):
        raise ValueError('Route incompatible avec SSH PTY')
    host=str(connection.get('host','')).strip()
    try: host=valid_host(host)
    except ValueError: raise ValueError('Hôte SSH invalide') from None
    port=int(connection.get('port') or 22)
    if not 1 <= port <= 65535:raise ValueError('Port SSH invalide')
    return host,port,str(connection.get('user') or '')

class PtyShell(QThread):
    received=Signal(str)
    state_message=Signal(str)
    closed=Signal()
    status=Signal(str)
    hop_diagnostic=Signal(str)
    def __init__(self,connection,route=None,parent=None):
        super().__init__(parent)
        self.target=validate_pty_target(connection,route)
        self.route=validate_route(route)
        self.jump_clients=[]
        self.jump_channels=[]
        self.jump_client=None
        self.jump_channel=None
        self.commands=queue.Queue()
        self.shutdown=threading.Event()
        self.client=None
        self.channel=None
        self._decoder=codecs.getincrementaldecoder("utf-8")("replace")
        self._connected=False
        self._last_rx=None
        self._last_tx=None
        self._keepalive_seconds=30
        self._hop_stage=None
        self._routed=None
    def _emit_status(self,state):
        signal=self.status
        if hasattr(signal,"emit"):signal.emit(state)
    def _hop(self,stage,outcome):
        self._hop_stage=stage
        self.hop_diagnostic.emit(hop_status(stage,outcome))

    def configure_keepalive(self, seconds):
        """Configure SSH transport keepalives, 0 disables; bounded to avoid flooding."""
        if not isinstance(seconds,int) or isinstance(seconds,bool) or seconds not in (0,*range(10,301)):
            raise ValueError("Intervalle keepalive invalide (0 ou 10-300 s)")
        if getattr(self, "isRunning", lambda: False)():
            raise RuntimeError("Configuration keepalive interdite pendant la session")
        self._keepalive_seconds=seconds

    def send_raw(self,text):
        if not isinstance(text,str) or len(text)>4096 or '\x00' in text:return False
        if self.shutdown.is_set():return False
        self.commands.put(('send',text));return True
    def send_text(self,text):
        if not isinstance(text,str) or len(text)>4096 or '\x00' in text:return False
        if self.shutdown.is_set():return False
        self.commands.put(('send',text+'\n'));return True
    def resize_pty(self,cols,rows):
        if not self.shutdown.is_set() and 20<=cols<=500 and 5<=rows<=200:self.commands.put(('resize',cols,rows))
    def stop(self):
        """Request cancellation and close the active channel to wake blocked reads."""
        self.shutdown.set()
        self._emit_status("stopping")
        channel=self.channel
        if channel is not None:
            try:channel.close()
            except OSError:pass
        channel=self.jump_channel
        if channel is not None:
            try:channel.close()
            except OSError:pass
        client=self.client
        if client is not None:
            try:client.close()
            except OSError:pass
        routed=self._routed
        if routed is not None:routed.close()
    def run(self):
        self._emit_status('connecting')
        routed=None
        try:
            host,port,user=self.target
            routed=RoutedSshClient({'host':host,'port':port,'user':user},self.route,
                on_stage=self._hop,keepalive=self._keepalive_seconds,cancelled=self.shutdown)
            self._routed=routed
            routed.connect()
            client=routed.target_client
            self.client=client
            self.jump_clients=routed.clients[:-1]
            self.jump_channels=routed.channels
            self.jump_client=self.jump_clients[-1] if self.jump_clients else None
            self.jump_channel=self.jump_channels[-1] if self.jump_channels else None
            if self.shutdown.is_set():return
            transport=client.get_transport()
            self._hop('target_pty','starting')
            channel=client.invoke_shell(term='xterm',width=100,height=30)
            self.channel=channel
            self._hop('target_pty','ok')
            if self.shutdown.is_set():return
            channel.settimeout(0.15)
            self._connected=True
            self._last_rx=time.monotonic()
            self._emit_status('connected')
            self.state_message.emit('PTY SSH connecté (émulation ANSI complète non disponible)')
            while not self.shutdown.is_set() and not channel.closed:
                while True:
                    try:command=self.commands.get_nowait()
                    except queue.Empty:break
                    if command[0]=='send':
                        channel.send(command[1])
                        self._last_tx=time.monotonic()
                    elif command[0]=='resize':channel.resize_pty(width=command[1],height=command[2])
                if not routed.transports_active():
                    raise ConnectionError("Transport SSH interrompu")
                if channel.recv_ready():
                    chunk=channel.recv(8192)
                    if not chunk:break
                    self._last_rx=time.monotonic()
                    decoded=self._decoder.decode(chunk,final=False)
                    if decoded:self.received.emit(decoded)
                else:self.msleep(50)
            channel.close()
            if not self.shutdown.is_set():
                self.state_message.emit('Connexion SSH terminée par le serveur.')
        except Exception as exc:
            if not self.shutdown.is_set():
                if self._hop_stage is not None:self._hop(self._hop_stage,'failed')
                self._emit_status('failed')
                self.state_message.emit(classify_failure(exc))
        finally:
            remaining=self._decoder.decode(b'',final=True)
            if remaining:self.received.emit(remaining)
            self.channel=None
            if routed is not None:routed.close()
            self._emit_status("closed")
            self.closed.emit()
