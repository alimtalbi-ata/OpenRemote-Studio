"""Protocol-neutral connection guard; no network operations performed here."""
from threading import RLock
from session_lifecycle import SessionLifecycle, State, InvalidTransition

class StaleAttempt(RuntimeError): pass

class ConnectionGuard:
    """Use a monotonically increasing attempt token to reject stale callbacks.

    The protocol adapter must invoke begin, success/failure, then close.
    This guard does not itself interrupt blocking I/O; adapters must implement timeouts.
    """
    def __init__(self, session_id, timeout_seconds=30):
        self.lifecycle=SessionLifecycle(session_id, timeout_seconds=timeout_seconds)
        self._lock=RLock()
        self._generation=0
        self._resource=None
    def begin(self):
        with self._lock:
            self.lifecycle.transition(State.CONNECTING)
            self._generation+=1
            return self._generation
    def _check(self, token):
        if token != self._generation: raise StaleAttempt('stale connection callback')
    def success(self, token, resource):
        """Adopt a resource only for a live attempt; dispose rejected resources.

        Caller owns resources if close() itself raises; failure is propagated.
        """
        with self._lock:
            try:
                self._check(token)
                if self.lifecycle.timed_out():
                    self.lifecycle.transition(State.FAILED)
                    raise TimeoutError('connection attempt expired')
                self.lifecycle.transition(State.CONNECTED)
            except (StaleAttempt, TimeoutError, InvalidTransition):
                if resource is not None:
                    resource.close()
                raise
            self._resource = resource
    def failure(self, token):
        with self._lock:
            self._check(token)
            self.lifecycle.transition(State.FAILED)
    def expire(self, now=None):
        with self._lock:
            return self.lifecycle.expire(now)
    def cancel(self):
        with self._lock:
            self._generation+=1
            return self.lifecycle.cancel()
    def close(self):
        with self._lock:
            self._generation+=1
            state=self.lifecycle.state
            if state is State.CLOSED:return
            if state is State.CONNECTED:self.lifecycle.transition(State.DISCONNECTING)
            elif state is State.CONNECTING:self.lifecycle.transition(State.DISCONNECTING)
            elif state is State.NEW:self.lifecycle.transition(State.CLOSED);return
            elif state is State.CANCELLED:self.lifecycle.transition(State.CLOSED);return
            elif state is State.FAILED:self.lifecycle.transition(State.CLOSED);return
            resource=self._resource
            self._resource=None
            try:
                if resource is not None:resource.close()
            except Exception:
                self.lifecycle.transition(State.FAILED)
                raise
            self.lifecycle.transition(State.CLOSED)
