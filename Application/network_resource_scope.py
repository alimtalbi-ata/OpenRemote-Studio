"""Lifecycle ownership and cooperative cancellation of network resources."""
from threading import Event, RLock, Thread


def close_quietly(resource):
    if resource is not None:
        try:
            resource.close()
        except Exception:
            pass


class NetworkResourceScope:
    """Thread-safe, idempotent scope; cancellation precedes resource cleanup.

    Network operations must check ``cancelled`` between blocking calls. Closing
    transports may interrupt I/O but cannot guarantee cancellation of every OS call.
    """
    def __init__(self):
        self._lock = RLock()
        self._closed = False
        self._resources = []
        self._cancel = Event()
        self._cleanup_done = Event()

    @property
    def closed(self):
        with self._lock:
            return self._closed

    @property
    def cancelled(self):
        return self._cancel.is_set()

    def register(self, resource):
        with self._lock:
            if not self._closed:
                self._resources.append(resource)
                return True
        close_quietly(resource)
        return False

    def close(self):
        with self._lock:
            if self._closed:
                return False
            self._closed = True
            self._cancel.set()
            resources = self._resources[::-1]
            self._resources.clear()

        def cleanup():
            try:
                for resource in resources:
                    close_quietly(resource)
            finally:
                self._cleanup_done.set()

        Thread(target=cleanup, name='network-resource-cleanup', daemon=True).start()
        return True

    def wait_closed(self, timeout=None):
        """Wait for registered-resource cleanup; never call on the GUI thread."""
        if not self.closed:
            return False
        return self._cleanup_done.wait(timeout)
