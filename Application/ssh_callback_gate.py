"""Thread-safe, Qt-independent delivery gate for asynchronous SSH results.

A result is checked at *delivery* time, not only at producer callback time.
This prevents queued UI events from resurrecting cancelled connections.
"""
from threading import RLock


class SSHCallbackGate:
    def __init__(self):
        self._lock = RLock()
        self._generation = 0
        self._closed = False

    def begin(self):
        with self._lock:
            if self._closed:
                raise RuntimeError('callback gate closed')
            self._generation += 1
            return self._generation

    def invalidate(self):
        with self._lock:
            self._generation += 1

    def close(self):
        with self._lock:
            self._closed = True
            self._generation += 1

    def deliver(self, generation, resource, receiver):
        """Deliver current result, or close stale result without holding gate lock.

        The receiver runs while holding the gate lock so cancellation cannot
        interleave between validation and delivery. Stale cleanup runs outside
        the lock because client.close() may block or invoke arbitrary callbacks.
        """
        with self._lock:
            stale = self._closed or generation != self._generation
            if not stale:
                receiver(resource)
                return True
        closer = getattr(resource, 'close', None)
        if callable(closer):
            closer()
        return False

    def deliver_error(self, generation, error, receiver):
        with self._lock:
            if self._closed or generation != self._generation:
                return False
            receiver(error)
            return True
