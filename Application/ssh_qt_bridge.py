"""Optional Qt SSH bridge with main-thread delivery-time generation validation.

Worker callbacks can run on background threads. No QWidget is touched here.
"""
from PySide6.QtCore import QObject, Signal, Slot, Qt, QThread
from ssh_callback_gate import SSHCallbackGate


class SSHQtBridge(QObject):
    connected = Signal(object)
    failed = Signal(str)
    _ready = Signal(int, object)
    _error_ready = Signal(int, object)

    def __init__(self, worker, parent=None):
        super().__init__(parent)
        self.worker = worker
        self._gate = SSHCallbackGate()
        # QueuedConnection ensures generation is rechecked in receiver's Qt thread.
        self._ready.connect(self._deliver_success, Qt.ConnectionType.QueuedConnection)
        self._error_ready.connect(self._deliver_error, Qt.ConnectionType.QueuedConnection)
        self._closed = False

    def _require_owner_thread(self):
        """Bridge operations and UI delivery must run on the owning Qt thread."""
        if QThread.currentThread() != self.thread():
            raise RuntimeError('SSHQtBridge must be used from its Qt owner thread')

    def start(self):
        self._require_owner_thread()
        if self._closed:
            raise RuntimeError('bridge closed')
        # Do not invalidate the current generation if the worker refuses a second start.
        if getattr(self.worker, 'is_connecting', False):
            raise RuntimeError('connection already in progress')
        generation = self._gate.begin()

        def success(resource):
            self._ready.emit(generation, resource)

        def failure(exc):
            self._error_ready.emit(generation, exc)

        try:
            return self.worker.connect(on_success=success, on_error=failure)
        except BaseException:
            # The worker can reject startup synchronously. Invalidate any
            # callbacks it emitted before raising, without masking the cause.
            self._gate.invalidate()
            raise

    @Slot(int, object)
    def _deliver_success(self, generation, resource):
        self._require_owner_thread()
        self._gate.deliver(generation, resource, self.connected.emit)

    @Slot(int, object)
    def _deliver_error(self, generation, error):
        self._require_owner_thread()
        self._gate.deliver_error(generation, error, lambda exc: self.failed.emit(f'{type(exc).__name__}: {exc}'))

    def cancel(self):
        self._require_owner_thread()
        if self._closed:
            return None
        self._gate.invalidate()
        return self.worker.cancel()

    def close(self):
        self._require_owner_thread()
        if self._closed:
            return
        self._closed = True
        self._gate.close()
        self.worker.close()
