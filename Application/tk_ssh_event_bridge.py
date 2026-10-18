"""Tkinter owner-thread event queue for SSH callbacks (V27.6).

No Tk method is invoked by the network worker. The UI owner calls drain()
from its own scheduled after() callback. Generation invalidation rejects stale
results and closes stale resources when possible.
"""
from queue import SimpleQueue, Empty
from threading import get_ident

class TkSSHEventBridge:
    def __init__(self, on_success, on_error):
        self._owner = get_ident()
        self._success = on_success
        self._error = on_error
        self._queue = SimpleQueue()
        self._generation = 0
        self._closed = False

    def _require_owner(self):
        if get_ident() != self._owner:
            raise RuntimeError('TkSSHEventBridge must be controlled by its UI thread')

    def begin(self):
        self._require_owner()
        if self._closed:
            raise RuntimeError('bridge closed')
        self._generation += 1
        return self._generation

    def post_success(self, generation, resource):
        self._queue.put(('success', generation, resource))

    def post_error(self, generation, error):
        self._queue.put(('error', generation, error))

    def invalidate(self):
        self._require_owner()
        self._generation += 1

    def close(self):
        self._require_owner()
        self._closed = True
        self._generation += 1
        self.drain()

    def drain(self, limit=100):
        self._require_owner()
        if limit < 1:
            raise ValueError('limit must be positive')
        count = 0
        while count < limit:
            try:
                kind, generation, value = self._queue.get_nowait()
            except Empty:
                break
            count += 1
            if self._closed or generation != self._generation:
                if kind == 'success':
                    closer = getattr(value, 'close', None)
                    if callable(closer):
                        closer()
                continue
            if kind == 'success':
                self._success(value)
            else:
                self._error(value)
        return count
