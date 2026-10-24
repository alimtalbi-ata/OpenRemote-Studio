"""R97: strict, bounded service inventory totals; no network or credentials.

The backend distinguishes a complete 128-service inventory from a truncated
one using a server-side count in the *same* fixed WinRM query. Legacy fixture
payloads remain supported but have unknown totals.
Author: Abdelhalim Talbi.
"""

MAX_SERVICES = 128
MAX_TOTAL = 1_000_000


class ServiceTotalError(ValueError):
    """Fixed code only; never include untrusted remote data in exceptions."""

    def __init__(self):
        super().__init__('winrm_invalid_response')


def unwrap_service_envelope(raw):
    """Return (total_count or None, rows), rejecting inconsistent counts.

    Legacy list or single-service dict responses are accepted for older tests
    and adapters, but their total is *unknown* (None), not inferred.
    """
    if not isinstance(raw, dict) or 'TotalCount' not in raw:
        return None, raw
    if set(raw) != {'TotalCount', 'Services'}:
        raise ServiceTotalError()
    count = raw['TotalCount']
    rows = raw['Services']
    if rows is None:
        rows = []
    if isinstance(rows, dict):
        rows = [rows]
    if (type(count) is not int or not 0 <= count <= MAX_TOTAL
            or not isinstance(rows, list) or len(rows) > MAX_SERVICES
            or len(rows) != min(count, MAX_SERVICES)):
        raise ServiceTotalError()
    return count, rows


def validated_display_total(total, rows, truncated):
    """Validate the backend/UI boundary; None means legacy unknown total."""
    if total is None:
        return None
    if (type(total) is not int or not 0 <= total <= MAX_TOTAL
            or not isinstance(rows, list)
            or len(rows) != min(total, MAX_SERVICES)
            or type(truncated) is not bool
            or truncated != (total > MAX_SERVICES)):
        raise ServiceTotalError()
    return total
