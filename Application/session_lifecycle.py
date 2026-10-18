"""Explicit, thread-safe session lifecycle state machine (V24.6)."""
from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from time import monotonic
from typing import Callable

class State(str, Enum):
    NEW = "new"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    CLOSED = "closed"
    FAILED = "failed"
    CANCELLED = "cancelled"

ALLOWED = {
    State.NEW: {State.CONNECTING, State.CANCELLED, State.CLOSED},
    State.CONNECTING: {State.CONNECTED, State.FAILED, State.CANCELLED, State.DISCONNECTING},
    State.CONNECTED: {State.DISCONNECTING, State.FAILED},
    State.DISCONNECTING: {State.CLOSED, State.FAILED},
    State.FAILED: {State.CONNECTING, State.CLOSED},
    State.CANCELLED: {State.CLOSED},
    State.CLOSED: set(),
}

class InvalidTransition(ValueError):
    pass

@dataclass
class SessionLifecycle:
    session_id: str
    state: State = State.NEW
    timeout_seconds: float = 30.0
    started_at: float | None = None
    history: list[tuple[str, str]] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def transition(self, target: State) -> State:
        with self._lock:
            if target not in ALLOWED[self.state]:
                raise InvalidTransition(f"{self.state.value} -> {target.value}")
            old = self.state
            self.state = target
            if target is State.CONNECTING:
                self.started_at = monotonic()
            elif target is not State.CONNECTING:
                self.started_at = None
            self.history.append((old.value, target.value))
            return self.state

    def timed_out(self, now: float | None = None) -> bool:
        with self._lock:
            return (self.state is State.CONNECTING and self.started_at is not None
                    and (monotonic() if now is None else now) - self.started_at >= self.timeout_seconds)

    def expire(self, now: float | None = None) -> bool:
        with self._lock:
            if not self.timed_out(now):
                return False
            self.transition(State.FAILED)
            return True

    def cancel(self) -> State:
        with self._lock:
            if self.state not in (State.NEW, State.CONNECTING):
                raise InvalidTransition("Cancellation not permitted in this state")
            return self.transition(State.CANCELLED)
