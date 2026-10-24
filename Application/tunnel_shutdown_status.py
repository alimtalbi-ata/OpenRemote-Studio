"""Non-blocking SSH tunnel shutdown status for GUI event loops.

Author: Abdelhalim Talbi. Call poll() on the UI thread; it never sleeps.
No credentials, hostnames or network endpoints are returned.
"""


class TunnelShutdownStatus:
    """Read-only shutdown state; never closes a caller-owned SSH client."""

    def __init__(self, scope, tunnel=None):
        self.scope = scope
        self.tunnel = tunnel

    def poll(self):
        """Return open/cleanup/draining/complete without waiting for I/O."""
        if not self.scope.closed:
            return 'open'
        if not self.scope.wait_closed(0):
            return 'cleanup'
        if self.tunnel is not None and not self.tunnel.wait_drained(0):
            return 'draining'
        return 'complete'
