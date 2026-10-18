"""Nonblocking SSH connection controller; optional integration boundary for Qt.

Callbacks are dispatched on the worker thread. Qt callers MUST forward results
through queued Qt signals, never update widgets from these callbacks.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from guarded_ssh_adapter import GuardedSSHAdapter
from session_lifecycle import InvalidTransition

class SSHAsyncWorker:
    def __init__(self, adapter: GuardedSSHAdapter, *, executor=None):
        self.adapter = adapter
        self._executor = executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix='ors-ssh')
        self._owns_executor = executor is None
        self._lock = Lock()
        self._closed = False
        self._future = None

    @property
    def is_connecting(self):
        """Thread-safe snapshot used by SSHQtBridge before advancing its generation."""
        with self._lock:
            return not self._closed and self._future is not None and not self._future.done()

    def connect(self, on_success=None, on_error=None):
        with self._lock:
            if self._closed:
                raise RuntimeError('worker closed')
            if self._future is not None and not self._future.done():
                raise RuntimeError('connection already in progress')
            def run():
                try:
                    result = self.adapter.connect()
                except Exception as exc:
                    if on_error:
                        on_error(exc)
                    return None
                else:
                    if on_success:
                        on_success(result)
                    return result
            # Executor shutdown/rejection must not leave a phantom busy state.
            # The assignment happens only after submit succeeds.
            future = self._executor.submit(run)
            self._future = future
            return future

    def cancel(self):
        # Invalidate generation; cannot interrupt a blocking Paramiko connect.
        return self.adapter.cancel()

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
        try:
            self.adapter.cancel()
        except InvalidTransition:
            pass  # Connected/failed sessions are closed, not cancelled.
        # Do not wait on network I/O on UI thread.
        if self._owns_executor:
            self._executor.shutdown(wait=False, cancel_futures=False)
        self.adapter.close()
