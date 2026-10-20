"""Qt background jobs, separated from UI. Author: Abdelhalim Talbi."""
from PySide6.QtCore import QObject, Signal, QRunnable
from threading import Event
from transfer_safety import download_atomic,upload_exclusive,download_resume_verified

class SftpSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    progress = Signal(int)

class SftpJob(QRunnable):
    """Run blocking Paramiko I/O away from the Qt GUI thread."""
    def __init__(self, connect_fn, connection, operation, remote_path, local_path=None):
        super().__init__()
        self.connect_fn=connect_fn; self.connection=dict(connection); self.operation=operation
        self.remote_path=remote_path; self.local_path=local_path
        self.signals=SftpSignals();self.cancel_event=Event()
    def cancel(self):
        self.cancel_event.set()

    def run(self):
        import stat
        client=None
        try:
            if self.cancel_event.is_set():raise InterruptedError('Opération annulée')
            client=self.connect_fn(self.connection)
            with client.open_sftp() as sftp:
                if self.cancel_event.is_set():raise InterruptedError('Opération annulée')
                if self.operation=='list':
                    result=[(x.filename, stat.S_ISDIR(x.st_mode), x.st_size) for x in sftp.listdir_attr(self.remote_path)]
                else:
                    def callback(done,total):
                        if self.cancel_event.is_set():raise InterruptedError('Opération annulée')
                        self.signals.progress.emit(int(done*100/total) if total else 100)
                    if self.operation=='upload':
                        upload_exclusive(sftp,self.local_path,self.remote_path,callback=callback,
                                         cancelled=self.cancel_event.is_set)
                    elif self.operation=='download':
                        download_atomic(sftp,self.remote_path,self.local_path,callback=callback,
                            cancelled=self.cancel_event.is_set)
                    elif self.operation=='resume_download':
                        download_resume_verified(sftp,self.remote_path,self.local_path,
                            self.connection['id'],callback=callback,
                                cancelled=self.cancel_event.is_set)
                    else:raise ValueError('Unknown SFTP operation')
                    result=True
            self.signals.finished.emit(result)
        except InterruptedError as exc:
            if self.cancel_event.is_set():
                self.signals.cancelled.emit()
            else:
                self.signals.failed.emit(f'{type(exc).__name__}: {exc}')
        except Exception as exc:
            self.signals.failed.emit(f'{type(exc).__name__}: {exc}')
        finally:
            if client:client.close()

class TcpJob(QRunnable):
    def __init__(self,host,port):
        super().__init__();self.host=host;self.port=port;self.signals=TcpSignals()
    def run(self):
        import socket
        try:
            with socket.create_connection((self.host,self.port),timeout=2):
                result='Accessible'
        except OSError as exc:result=f'Indisponible : {exc}'
        self.signals.finished.emit(f'TCP {self.host}:{self.port} — {result}')

class TcpSignals(QObject):
    finished=Signal(str)


class SshPathJob(QRunnable):
    def __init__(self,connection,route):
        super().__init__();self.connection=connection;self.route=route;self.signals=TcpSignals()
    def run(self):
        from ssh_path_probe import check
        result=check(self.connection,self.route)
        self.signals.finished.emit(result['message'])


class SshHopLocalJob(QRunnable):
    """One background task, sequential bounded TCP probes; no SSH credentials."""
    def __init__(self,hops):
        super().__init__();self.hops=[dict(h) for h in hops];self.signals=HopProbeSignals()
    def run(self):
        from ssh_hop_probe import check
        try:self.signals.finished.emit(check(self.hops))
        except (OSError,ValueError,TypeError):
            self.signals.finished.emit([{'index':0,'status':'error','message':'Diagnostic local indisponible.'}])

class HopProbeSignals(QObject):
    finished=Signal(object)


class SshEndToEndSignals(QObject):
    finished=Signal(object)
    progress=Signal(object)

class SshEndToEndJob(QRunnable):
    """Explicitly authorized real SSH authentication, off the UI thread."""
    def __init__(self,hops,target,port,user,connect_timeout=10):
        super().__init__()
        self.hops=[dict(h) for h in hops]
        self.target=target;self.port=port;self.user=user;self.connect_timeout=connect_timeout
        self.signals=SshEndToEndSignals()
        self.cancel_event=Event()
    def cancel(self):
        self.cancel_event.set()
    def run(self):
        from ssh_end_to_end_probe import probe
        try:result=probe(self.hops,self.target,self.port,self.user,consent=True,
                             cancelled=self.cancel_event,on_event=self.signals.progress.emit,
                             connect_timeout=self.connect_timeout)
        except Exception:
            result={'status':'failed','events':[], 'message':'Diagnostic SSH indisponible.'}
        self.signals.finished.emit(result)
