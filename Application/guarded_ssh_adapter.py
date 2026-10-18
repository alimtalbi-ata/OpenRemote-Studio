"""Opt-in guarded SSH adapter; preserves the legacy route until integration is qualified."""
from session_connection_guard import ConnectionGuard


class GuardedSSHAdapter:
    """Wrap a synchronous SSH client factory with generation-based ownership.

    The factory must implement its own bounded connect timeout. This adapter does
    not interrupt a blocking connect; cancellation rejects and closes late results.
    """
    def __init__(self, session_id, connect_factory, timeout_seconds=30):
        self.guard = ConnectionGuard(session_id, timeout_seconds)
        self.connect_factory = connect_factory

    def connect(self):
        token = self.guard.begin()
        try:
            client = self.connect_factory()
        except Exception:
            try:
                self.guard.failure(token)
            except Exception:
                pass  # A cancelled or superseded attempt must retain its state.
            raise
        self.guard.success(token, client)
        return client

    def cancel(self):
        return self.guard.cancel()

    def close(self):
        return self.guard.close()
