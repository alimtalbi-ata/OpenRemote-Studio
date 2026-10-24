"""Revision-bound, non-secret SSH tunnel consent state.

No hostname, username, private-key path or credential is retained here.
Author: Abdelhalim Talbi.
"""


class SSHConsentGuard:
    """A one-shot approval applies only to the current configuration revision."""

    def __init__(self):
        self._revision = 0
        self._approved_revision = None

    def configuration_changed(self):
        self._revision += 1
        self._approved_revision = None

    def approve(self):
        self._approved_revision = self._revision

    def revoke(self):
        self._approved_revision = None

    @property
    def approved(self):
        return self._approved_revision is not None and self._approved_revision == self._revision
