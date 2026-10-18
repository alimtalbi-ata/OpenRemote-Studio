"""Secure SSH tunnel and SFTP helpers. Author: Abdelhalim Talbi."""
import socket, select, socketserver, threading
from pathlib import PurePosixPath

def safe_remote_path(base, name):
    if not name or name in ('.', '..') or '/' in name or "\\" in name or "\x00" in name:
        raise ValueError('Nom de fichier distant invalide')
    return str(PurePosixPath(base) / name)

class Tunnel:
    def __init__(self, client, bind_host, bind_port, target_host, target_port):
        if bind_host not in ('127.0.0.1', '::1', 'localhost'):
            raise ValueError('Écoute locale uniquement pour éviter une exposition réseau')
        for port in (bind_port, target_port):
            if not 1 <= int(port) <= 65535: raise ValueError('Port invalide')
        transport = client.get_transport()
        if not transport or not transport.is_active(): raise RuntimeError('SSH déconnecté')
        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                channel = transport.open_channel('direct-tcpip', (target_host, int(target_port)), self.request.getpeername())
                if channel is None: return
                try:
                    while True:
                        ready, _, _ = select.select([self.request, channel], [], [], 1)
                        if self.request in ready:
                            data = self.request.recv(32768)
                            if not data: break
                            channel.sendall(data)
                        if channel in ready:
                            data = channel.recv(32768)
                            if not data: break
                            self.request.sendall(data)
                finally: channel.close()
        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True
        self.server = Server((bind_host, int(bind_port)), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
    def start(self): self.thread.start()
    def close(self): self.server.shutdown(); self.server.server_close()
